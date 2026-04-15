from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from skilllint.config import SkillLintConfig
from skilllint.models import Confidence, Evidence, Finding, Severity, severity_rank


@dataclass(frozen=True)
class LLMCandidate:
    # LLM 不直接分析整仓库，只分析少量“可解释的候选片段”。
    file: str
    line_start: int | None
    line_end: int | None
    snippet: str
    hint: str


@dataclass(frozen=True)
class SemanticLabelSpec:
    """LLM 可返回的稳定语义标签定义。

    注意这里不是直接暴露内部 rule catalog，而是定义一套对外部模型更容易理解的
    plain-language labels，再由本地代码映射回 SkillLint 的 taxonomy 与 rule_id。
    """
    label: str
    title: str
    taxonomy: str
    description: str
    default_remediation: str
    related_taxonomy: tuple[str, ...] = ()
    secondary_tags: tuple[str, ...] = ("semantic", "llm")

    @property
    def rule_id(self) -> str:
        return f"LLM_LABEL_{self.label.upper()}"


SEMANTIC_LABEL_SPECS: dict[str, SemanticLabelSpec] = {
    "hidden_behavior": SemanticLabelSpec(
        label="hidden_behavior",
        title="Hidden behavior or user nondisclosure instruction",
        taxonomy="SLT-A02",
        description="The snippet hides behavior from the user, asks not to mention side effects, or pushes silent actions.",
        default_remediation="Remove hidden-behavior instructions and surface sensitive actions to the user.",
    ),
    "disguised_exfiltration": SemanticLabelSpec(
        label="disguised_exfiltration",
        title="Disguised exfiltration as support or compliance workflow",
        taxonomy="SLT-B01",
        description="The snippet frames sending data outward as audit, support, telemetry, backup, or compliance work.",
        default_remediation="Remove disguised outbound transfer steps or require explicit approval and destination allowlisting.",
    ),
    "embedded_instruction_following": SemanticLabelSpec(
        label="embedded_instruction_following",
        title="Follows embedded instructions from external content",
        taxonomy="SLT-A03",
        description="The snippet treats instructions found in external content as authority to execute.",
        default_remediation="Treat external content as data, not authority; do not follow embedded operational instructions.",
    ),
    "trigger_hijack": SemanticLabelSpec(
        label="trigger_hijack",
        title="Over-broad skill scope or trigger hijacking",
        taxonomy="SLT-A05",
        description="The snippet claims an overly broad scope that may hijack routing or overlap with unrelated capabilities.",
        default_remediation="Narrow the scope and make trigger conditions more specific.",
    ),
    "tool_poisoning": SemanticLabelSpec(
        label="tool_poisoning",
        title="Suspicious tool orchestration or tool-description poisoning",
        taxonomy="SLT-B05",
        description="The snippet silently routes through tools or embeds hidden instructions inside tool descriptions or tool use policy.",
        default_remediation="Keep tool descriptions declarative and require explicit user approval for action tools.",
    ),
    "remote_dynamic_instructions": SemanticLabelSpec(
        label="remote_dynamic_instructions",
        title="Remote dynamic instruction loading",
        taxonomy="SLT-C02",
        description="The snippet loads effective instructions, prompts, or workflow rules from a remote source at runtime.",
        default_remediation="Keep reviewed instructions local, or pin remote content with versioning and integrity checks.",
    ),
    "memory_persistence": SemanticLabelSpec(
        label="memory_persistence",
        title="Writes risky instructions into persistent memory or profile",
        taxonomy="SLT-B04",
        description="The snippet persists risky instructions, profile changes, or memory entries across future sessions.",
        default_remediation="Limit persistent memory writes to explicit, user-approved, low-risk data.",
    ),
    "destructive_chain": SemanticLabelSpec(
        label="destructive_chain",
        title="Destructive or ransom-like action chain",
        taxonomy="SLT-B02",
        description="The snippet bulk deletes, encrypts, wipes, or archive-then-deletes files or workspace state.",
        default_remediation="Remove destructive workflows or require narrowly scoped, explicit confirmation for each destructive action.",
    ),
    "ci_untrusted_context": SemanticLabelSpec(
        label="ci_untrusted_context",
        title="CI or automation prompt may trust untrusted issue or PR text",
        taxonomy="SLT-D01",
        description="The snippet feeds issue, PR, or comment content directly into agent automation as instructions.",
        default_remediation="Treat CI event payloads as untrusted data and isolate agent actions with strict permission boundaries.",
    ),
    "credential_collection": SemanticLabelSpec(
        label="credential_collection",
        title="Conversational collection of secrets or credentials",
        taxonomy="SLT-E01",
        description="The snippet asks users to provide API keys, tokens, passwords, or other secrets in chat or plain text.",
        default_remediation="Use secure secret provisioning mechanisms instead of collecting credentials in chat.",
    ),
    "permission_drift": SemanticLabelSpec(
        label="permission_drift",
        title="Declared low-risk behavior conflicts with risky capabilities",
        taxonomy="SLT-E03",
        description="The snippet claims read-only or low-risk behavior while also implying write, execution, or network actions.",
        default_remediation="Align the description with actual capabilities or remove the risky behavior.",
    ),
    "prompt_priority_override": SemanticLabelSpec(
        label="prompt_priority_override",
        title="Priority override or coercive prompt control",
        taxonomy="SLT-A01",
        description="The snippet tries to override instruction hierarchy or force hidden higher-priority behavior.",
        default_remediation="Remove coercive priority language and require explicit user confirmation for sensitive actions.",
        related_taxonomy=("SLT-A02",),
    ),
    "network_exfiltration": SemanticLabelSpec(
        label="network_exfiltration",
        title="Sensitive data exfiltration or external transmission",
        taxonomy="SLT-B01",
        description="The snippet sends conversations, files, credentials, or other sensitive content to an external destination.",
        default_remediation="Remove outbound transfer steps or require explicit approval and destination allowlisting.",
    ),
    "dangerous_execution": SemanticLabelSpec(
        label="dangerous_execution",
        title="Dangerous command execution path",
        taxonomy="SLT-E02",
        description="The snippet builds or forwards potentially untrusted input into shell, eval, subprocess, or similar execution sinks.",
        default_remediation="Avoid shell-style execution of untrusted input; use structured, allowlisted operations instead.",
    ),
    "persistence_mechanism": SemanticLabelSpec(
        label="persistence_mechanism",
        title="Persistence or startup modification mechanism",
        taxonomy="SLT-B06",
        description="The snippet establishes persistence through startup hooks, file monitoring, reverse shells, or background mechanisms.",
        default_remediation="Remove persistence behavior unless it is explicitly required, visible, and tightly scoped.",
        related_taxonomy=("SLT-C04",),
    ),
    "supply_chain_bootstrap": SemanticLabelSpec(
        label="supply_chain_bootstrap",
        title="Remote bootstrap or install chain",
        taxonomy="SLT-C01",
        description="The snippet installs or bootstraps behavior through remote scripts, package lifecycle hooks, or unreviewed installers.",
        default_remediation="Prefer pinned, reviewed local installers and avoid piping remote scripts directly into a shell.",
        related_taxonomy=("SLT-C04",),
    ),
}


class LLMAnalyzer:
    """Optional OpenAI-compatible semantic analyzer.

    The analyzer is intentionally conservative: it only reviews a small number
    of already suspicious snippets and may return zero findings.
    """

    def __init__(self, config: SkillLintConfig) -> None:
        self.config = config
        self._client: Any | None = None
        self._status = "disabled"
        self._debug_records: list[dict[str, Any]] = []

    @property
    def status(self) -> str:
        # status 主要给上层 metadata / 调试信息使用。
        return self._status

    @property
    def debug_records(self) -> list[dict[str, Any]]:
        return list(self._debug_records)

    def analyze(self, candidates: list[LLMCandidate]) -> list[Finding]:
        # debug 记录是一次 analyze 调用级别的，因此每轮开始前清空。
        self._debug_records = []
        if not candidates:
            self._status = "no-candidates"
            return []
        client = self._get_client()
        if client is None:
            return []

        findings: list[Finding] = []
        # 限制候选数量，控制成本、延迟与不稳定性。
        for candidate in candidates[:6]:
            response_data = self._analyze_candidate(client, candidate)
            findings.extend(self._build_findings(candidate, response_data))
        self._status = "used"
        return _dedupe_findings(findings)

    def _build_findings(self, candidate: LLMCandidate, response_data: dict[str, Any]) -> list[Finding]:
        # 外部 LLM 返回 plain-language label，本地再映射为稳定 rule_id / taxonomy。
        findings: list[Finding] = []
        for item in response_data.get("findings", []):
            label = _normalize_label(item.get("label"))
            if label is None:
                continue
            spec = SEMANTIC_LABEL_SPECS[label]
            severity = _normalize_severity(item.get("severity"))
            confidence = _normalize_confidence(item.get("confidence"))
            related_taxonomy = list(spec.related_taxonomy)
            for related_label in item.get("related_labels") or []:
                normalized_related = _normalize_label(related_label)
                if normalized_related is None:
                    continue
                related_taxonomy.append(SEMANTIC_LABEL_SPECS[normalized_related].taxonomy)
            findings.append(
                Finding(
                    id=str(uuid4()),
                    rule_id=spec.rule_id,
                    title=item.get("title") or spec.title,
                    severity=severity,
                    confidence=confidence,
                    engine="semantic-llm",
                    primary_taxonomy=spec.taxonomy,
                    related_taxonomy=sorted(dict.fromkeys(related_taxonomy)),
                    secondary_tags=list(spec.secondary_tags),
                    explanation=item.get("explanation"),
                    remediation=item.get("remediation") or spec.default_remediation,
                    evidence=Evidence(
                        file=candidate.file,
                        line_start=candidate.line_start,
                        line_end=candidate.line_end,
                        snippet=candidate.snippet,
                    ),
                    metadata={
                        "hint": candidate.hint,
                        "llm_label": label,
                        "llm_label_description": spec.description,
                    },
                )
            )
        return findings

    def _get_client(self) -> Any | None:
        # 优先读取当前 config，再回退到环境变量，便于 CLI / Web 两种入口共享同一实现。
        api_key = self.config.llm.api_key or os.getenv("SKILLLINT_LLM_API_KEY")
        if not api_key:
            self._status = "missing-api-key"
            return None
        model = self.config.llm.model or os.getenv("SKILLLINT_LLM_MODEL")
        if not model:
            self._status = "missing-model"
            return None
        try:
            from openai import OpenAI
        except Exception:
            self._status = "openai-import-failed"
            return None

        if self._client is None:
            base_url = self.config.llm.base_url or os.getenv("SKILLLINT_LLM_BASE_URL")
            kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            # 这里使用 OpenAI-compatible client，方便接标准 OpenAI 与兼容网关。
            self._client = OpenAI(**kwargs)
        return self._client

    def _analyze_candidate(self, client: Any, candidate: LLMCandidate) -> dict[str, Any]:
        prompt = _build_prompt(candidate)
        try:
            # 要求 response_format=json_object，尽量降低解析不稳定性。
            response = client.chat.completions.create(
                model=self.config.llm.model or os.getenv("SKILLLINT_LLM_MODEL"),
                temperature=self.config.llm.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a security analyzer for agent skills. "
                            "Only report concrete, snippet-grounded findings. "
                            "Use only the provided semantic labels and return JSON with a top-level 'findings' array."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content or '{"findings": []}'
            parsed = json.loads(content)
            self._record_debug(
                candidate=candidate,
                raw_content=content,
                parsed_response=parsed,
            )
            return parsed
        except Exception as exc:
            self._status = f"llm-error:{type(exc).__name__}"
            self._record_debug(
                candidate=candidate,
                error=f"{type(exc).__name__}: {exc}",
            )
            return {"findings": []}

    def _record_debug(
        self,
        *,
        candidate: LLMCandidate,
        raw_content: str | None = None,
        parsed_response: dict[str, Any] | None = None,
        error: str | None = None,
    ) -> None:
        if not self.config.llm.debug:
            return
        self._debug_records.append(
            {
                "file": candidate.file,
                "line_start": candidate.line_start,
                "line_end": candidate.line_end,
                "hint": candidate.hint,
                "snippet": candidate.snippet,
                "raw_content": raw_content,
                "parsed_response": parsed_response,
                "error": error,
            }
        )


def _build_prompt(candidate: LLMCandidate) -> str:
    # prompt 不暴露内部 taxonomy code 语义，避免让外部模型“硬猜内部编码体系”。
    labels_text = "\n".join(
        f"- {spec.label}: {spec.description}" for spec in SEMANTIC_LABEL_SPECS.values()
    )
    return f"""
Review this skill snippet and decide whether it contains a likely security issue.

Allowed semantic labels:
{labels_text}

Rules:
- Report zero findings if the snippet looks benign, defensive, or ambiguous.
- Only use evidence from this snippet.
- Choose labels from the allowed list only.
- Keep explanations short and concrete.
- Prefer one to three precise findings instead of over-reporting.

Return JSON:
{{
  "findings": [
    {{
      "label": "one_allowed_label",
      "related_labels": ["optional_allowed_label"],
      "title": "optional short title",
      "severity": "low|medium|high|critical",
      "confidence": "low|medium|high",
      "explanation": "short snippet-grounded reason",
      "remediation": "short remediation"
    }}
  ]
}}

File: {candidate.file}
Line range: {candidate.line_start}-{candidate.line_end}
Hint: {candidate.hint}
Snippet:
{candidate.snippet}
""".strip()


def _normalize_label(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = value.strip().lower().replace("-", "_").replace(" ", "_")
    if normalized in SEMANTIC_LABEL_SPECS:
        return normalized
    return None


def _normalize_severity(value: Any) -> Severity:
    if value in {"info", "low", "medium", "high", "critical"}:
        return value
    return "medium"


def _normalize_confidence(value: Any) -> Confidence:
    if value in {"low", "medium", "high"}:
        return value
    return "medium"


def _dedupe_findings(findings: list[Finding]) -> list[Finding]:
    # 不同候选片段可能会让 LLM 重复报告同一逻辑问题，因此要做二次去重。
    deduped: list[Finding] = []
    for finding in findings:
        matched_index: int | None = None
        for idx, existing in enumerate(deduped):
            if _findings_equivalent(existing, finding):
                matched_index = idx
                break
        if matched_index is None:
            deduped.append(finding)
            continue
        deduped[matched_index] = _merge_duplicate_findings(deduped[matched_index], finding)
    return deduped


def _merge_duplicate_findings(left: Finding, right: Finding) -> Finding:
    if _finding_strength(right) > _finding_strength(left):
        primary, secondary = right, left
    else:
        primary, secondary = left, right
    hints = []
    for finding in [primary, secondary]:
        hint = finding.metadata.get("hint")
        if hint:
            hints.append(str(hint))
        hints.extend(str(item) for item in finding.metadata.get("hints", []))
    merged_metadata = dict(primary.metadata)
    merged_metadata["hints"] = sorted(dict.fromkeys(hints))
    merged_metadata["deduped_count"] = int(left.metadata.get("deduped_count", 1)) + int(right.metadata.get("deduped_count", 1))
    primary.metadata = merged_metadata
    primary.related_taxonomy = sorted(dict.fromkeys([*primary.related_taxonomy, *secondary.related_taxonomy]))
    return primary


def _finding_strength(finding: Finding) -> tuple[int, int]:
    # 去重合并时优先保留“更高 severity / confidence”的那条 finding。
    confidence_order = {"low": 0, "medium": 1, "high": 2}
    return severity_rank(finding.severity), confidence_order[finding.confidence]


def _findings_equivalent(left: Finding, right: Finding) -> bool:
    if left.rule_id != right.rule_id:
        return False
    if left.evidence.file != right.evidence.file:
        return False
    if left.metadata.get("llm_label") != right.metadata.get("llm_label"):
        return False

    left_snippet = _normalize_snippet(left.evidence.snippet)
    right_snippet = _normalize_snippet(right.evidence.snippet)
    if left_snippet and right_snippet:
        if left_snippet == right_snippet:
            return True
        if left_snippet in right_snippet or right_snippet in left_snippet:
            return True

    return _line_ranges_overlap(
        left.evidence.line_start,
        left.evidence.line_end,
        right.evidence.line_start,
        right.evidence.line_end,
    )


def _normalize_snippet(snippet: str | None) -> str:
    if not snippet:
        return ""
    return " ".join(snippet.lower().split())


def _line_ranges_overlap(
    left_start: int | None,
    left_end: int | None,
    right_start: int | None,
    right_end: int | None,
) -> bool:
    if left_start is None or right_start is None:
        return False
    left_end = left_end or left_start
    right_end = right_end or right_start
    return max(left_start, right_start) <= min(left_end, right_end)
