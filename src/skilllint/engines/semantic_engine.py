from __future__ import annotations

from collections import defaultdict
from pathlib import Path

from skilllint.config import SkillLintConfig
from skilllint.core.workspace import PreparedWorkspace
from skilllint.engines.base import Engine
from skilllint.engines.llm_analyzer import LLMAnalyzer, LLMCandidate
from skilllint.models import Evidence, Finding
from skilllint.rules.repository import SemanticRule, build_finding, get_rule_repository
from skilllint.rules.selector import RuleSelector
from skilllint.utils.files import extract_snippet, is_text_file, line_range_for_offset, read_text

IGNORED_SEMANTIC_FILENAMES = {"LICENSE", "LICENSE.txt", "COPYING", "NOTICE"}


class SemanticEngine(Engine):
    name = "semantic"

    def __init__(self, config: SkillLintConfig, selector: RuleSelector | None = None) -> None:
        self.config = config
        self.selector = selector or RuleSelector()
        self.llm = LLMAnalyzer(config)
        self.last_llm_status = "disabled"
        repository = get_rule_repository()
        self.keyword_groups = repository.semantic_keyword_groups
        self.catalog_rules = [
            rule
            for rule in repository.semantic_rules
            if self.selector.allows_rule(rule.rule_id, rule.taxonomy)
        ]
        self.permission_drift_rule = next(
            (rule for rule in self.catalog_rules if rule.rule_id == "SEMANTIC_PERMISSION_DRIFT"),
            None,
        )
        self.match_rules = [
            rule
            for rule in self.catalog_rules
            if rule.metadata.get("detection") != "permission_drift"
        ]

    def run(
        self,
        workspace: PreparedWorkspace,
        seed_findings: list[Finding] | None = None,
    ) -> list[Finding]:
        seed_findings = seed_findings or []
        findings: list[Finding] = []
        llm_candidates: list[LLMCandidate] = []
        file_seed = defaultdict(list)
        for finding in seed_findings:
            if finding.evidence.file:
                file_seed[finding.evidence.file].append(finding)

        seen: set[tuple[str, str, int, int]] = set()
        for path in workspace.all_files():
            if not path.is_file() or not is_text_file(path):
                continue
            rel = workspace.relpath(path)
            if path.name in IGNORED_SEMANTIC_FILENAMES:
                continue
            try:
                text = read_text(path)
            except OSError:
                continue
            if not text.strip():
                continue

            findings.extend(
                self._scan_text(
                    path=path,
                    rel=rel,
                    text=text,
                    seed_findings=file_seed.get(rel, []),
                    seen=seen,
                    llm_candidates=llm_candidates,
                )
            )

        if self.config.engines.semantic.use_llm:
            findings.extend(self.llm.analyze(_unique_candidates(llm_candidates)))
            self.last_llm_status = self.llm.status
        else:
            self.last_llm_status = "disabled"

        return findings

    def _scan_text(
        self,
        path: Path,
        rel: str,
        text: str,
        seed_findings: list[Finding],
        seen: set[tuple[str, str, int, int]],
        llm_candidates: list[LLMCandidate],
    ) -> list[Finding]:
        findings: list[Finding] = []
        lower = text.lower()

        for finding in seed_findings:
            if finding.evidence.snippet:
                llm_candidates.append(
                    LLMCandidate(
                        file=rel,
                        line_start=finding.evidence.line_start,
                        line_end=finding.evidence.line_end,
                        snippet=finding.evidence.snippet,
                        hint=f"seed finding {finding.rule_id}",
                    )
                )

        for rule in self.match_rules:
            if not rule.applies_to_path(rel):
                continue
            match_range = _semantic_rule_match_range(rule, text, self.keyword_groups)
            if match_range is None:
                continue
            start, end, segment = match_range
            if _semantic_rule_suppressed(rule, segment):
                continue
            line_start, line_end = line_range_for_offset(text, start, end)
            key = (rule.rule_id, rel, line_start, line_end)
            if key in seen:
                continue
            seen.add(key)
            snippet = extract_snippet(text, line_start, line_end, radius=2)
            findings.append(
                build_finding(
                    rule=rule,
                    engine=self.name,
                    evidence=Evidence(
                        file=rel,
                        line_start=line_start,
                        line_end=line_end,
                        snippet=snippet,
                    ),
                )
            )
            llm_candidates.append(
                LLMCandidate(
                    file=rel,
                    line_start=line_start,
                    line_end=line_end,
                    snippet=snippet,
                    hint=rule.hint_group or rule.rule_id.lower(),
                )
            )

        if self.permission_drift_rule is not None and self.permission_drift_rule.applies_to_path(rel) and _contains_any(
            lower, self.keyword_groups.get("read_only_claim", [])
        ) and _permission_drift_supported(
            text=text,
            dangerous_capability_keywords=self.keyword_groups.get("dangerous_capability", []),
            seed_findings=seed_findings,
        ):
            line_start, line_end, snippet = _first_matching_line(
                text,
                self.keyword_groups.get("read_only_claim", []),
            )
            key = (self.permission_drift_rule.rule_id, rel, line_start, line_end)
            if key not in seen:
                seen.add(key)
                findings.append(
                    build_finding(
                        rule=self.permission_drift_rule,
                        engine=self.name,
                        related_taxonomy=[
                            f.primary_taxonomy for f in seed_findings if f.primary_taxonomy
                        ][:2],
                        evidence=Evidence(
                            file=rel,
                            line_start=line_start,
                            line_end=line_end,
                            snippet=snippet,
                        ),
                    )
                )
                llm_candidates.append(
                    LLMCandidate(
                        file=rel,
                        line_start=line_start,
                        line_end=line_end,
                        snippet=snippet,
                        hint="permission-drift",
                    )
                )

        return findings



def _semantic_rule_match_range(
    rule: SemanticRule,
    text: str,
    keyword_groups: dict[str, list[str]],
) -> tuple[int, int, str] | None:
    segments = _segment_ranges(text)
    for start, end in segments:
        segment = text[start:end]
        lowered = segment.lower()
        all_of = rule.all_of_groups or []
        any_of = rule.any_of_groups or []
        if all_of and not all(_contains_any(lowered, keyword_groups.get(group, [])) for group in all_of):
            continue
        if any_of and not any(_contains_any(lowered, keyword_groups.get(group, [])) for group in any_of):
            continue
        if all_of or any_of:
            return start, end, segment
    return None



def _semantic_rule_suppressed(rule: SemanticRule, segment: str) -> bool:
    lowered = segment.lower()
    defensive_terms = [
        "do not use",
        "must not",
        "avoid",
        "warning",
        "caution",
        "not needed",
        "not recommended",
        "不要使用",
        "避免",
        "警告",
        "注意",
    ]
    analytical_terms = [
        "threat model",
        "attacker goals",
        "abuse paths",
        "classify each threat",
        "illustrative",
        "attack class",
        "identify entry points",
        "entry points",
        "trust boundaries",
        "assets that drive risk",
        "风险优先级",
        "攻击路径",
        "威胁建模",
    ]
    explicit_concealment = [
        "do not mention",
        "without telling the user",
        "do not bother the user",
        "不要告诉用户",
        "不要打扰用户",
        "静默上报",
    ]
    cleanup_terms = [
        "cleanup",
        "clean up",
        "temporary",
        "temp_dir",
        "temp dir",
        "node_modules",
        "lockfile",
        "package-lock",
        "pnpm-lock",
        "yarn.lock",
    ]
    if rule.rule_id == "SEMANTIC_HIDDEN_BEHAVIOR":
        if any(term in lowered for term in explicit_concealment):
            return False
        if any(term in lowered for term in defensive_terms):
            return True
    if rule.rule_id == "SEMANTIC_EXFIL_MASQUERADE" and any(term in lowered for term in analytical_terms):
        return True
    if rule.rule_id == "SEMANTIC_DESTRUCTIVE_CHAIN" and any(term in lowered for term in cleanup_terms):
        return True
    return False



def _contains_any(text: str, keywords: list[str]) -> bool:
    return any(keyword.lower() in text for keyword in keywords)



def _segment_ranges(text: str) -> list[tuple[int, int]]:
    segments: list[tuple[int, int]] = []
    start = 0
    for chunk in text.split("\n\n"):
        end = start + len(chunk)
        if chunk.strip():
            segments.append((start, end))
        start = end + 2
    return segments or [(0, min(len(text), 240))]



def _first_matching_line(text: str, keywords: list[str]) -> tuple[int, int, str]:
    for idx, line in enumerate(text.splitlines(), start=1):
        lowered = line.lower()
        if any(keyword.lower() in lowered for keyword in keywords):
            return idx, idx, extract_snippet(text, idx, idx, radius=1)
    return 1, 1, extract_snippet(text, 1, 1, radius=1)


def _permission_drift_supported(
    *,
    text: str,
    dangerous_capability_keywords: list[str],
    seed_findings: list[Finding],
) -> bool:
    line_start, _, snippet = _first_matching_line(
        text,
        ["read-only", "only reads", "does not modify", "只读", "仅做读取", "不会修改"],
    )
    local_context = extract_snippet(text, line_start, line_start, radius=6).lower()
    if _contains_any(local_context, dangerous_capability_keywords):
        return True
    nearby_lines = {line for line in range(max(1, line_start - 6), line_start + 7)}
    return any(
        finding.evidence.line_start in nearby_lines
        for finding in seed_findings
        if finding.evidence.line_start is not None
    )



def _unique_candidates(candidates: list[LLMCandidate]) -> list[LLMCandidate]:
    seen: set[tuple[str, int | None, int | None, str]] = set()
    unique: list[LLMCandidate] = []
    for candidate in candidates:
        key = (
            candidate.file,
            candidate.line_start,
            candidate.line_end,
            candidate.snippet.strip(),
        )
        if key in seen:
            continue
        seen.add(key)
        unique.append(candidate)
    return unique
