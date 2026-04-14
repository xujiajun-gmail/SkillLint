from __future__ import annotations

from collections import Counter, defaultdict
from dataclasses import dataclass
from uuid import uuid4

from skilllint.models import CorrelationHit, Evidence, Finding, ScanSummary, Severity, severity_rank

BASE_SEVERITY_SCORE: dict[Severity, int] = {
    "info": 5,
    "low": 15,
    "medium": 35,
    "high": 60,
    "critical": 90,
}

CONFIDENCE_MULTIPLIER = {
    "low": 0.6,
    "medium": 0.85,
    "high": 1.0,
}

ENGINE_BONUS = {
    "package": 2,
    "regex": 4,
    "semantic": 6,
    "dataflow": 10,
    "correlation": 0,
}

MALICIOUS_RULE_IDS = {
    "REVERSE_SHELL_PATTERN",
    "DATAFLOW_SECRET_TO_NETWORK",
    "DATAFLOW_SHELL_SECRET_TO_NETWORK",
    "CORRELATED_SECRET_EXFIL_CHAIN",
    "CORRELATED_PRIORITY_EXFIL",
}


@dataclass(frozen=True)
class CorrelationPattern:
    correlation_id: str
    title: str
    required_rules: frozenset[str]
    score: int
    rationale: str
    synthetic_rule_id: str | None = None
    synthetic_title: str | None = None
    synthetic_severity: Severity | None = None
    synthetic_taxonomy: str | None = None
    synthetic_related_taxonomy: tuple[str, ...] = ()
    synthetic_tags: tuple[str, ...] = ()
    synthetic_explanation: str | None = None
    synthetic_remediation: str | None = None


PATTERNS: tuple[CorrelationPattern, ...] = (
    CorrelationPattern(
        correlation_id="secret_exfil_chain",
        title="Sensitive read plus external send chain",
        required_rules=frozenset({"SECRET_PATH_ACCESS", "NETWORK_EXFIL_SEND"}),
        score=45,
        rationale="同一文件同时读取敏感路径并向外发送数据，构成高置信度泄露链。",
        synthetic_rule_id="CORRELATED_SECRET_EXFIL_CHAIN",
        synthetic_title="Sensitive read plus external send chain",
        synthetic_severity="critical",
        synthetic_taxonomy="SLT-B01",
        synthetic_related_taxonomy=("SLT-E02",),
        synthetic_tags=("confidentiality", "dataflow", "pattern_match"),
        synthetic_explanation="The same file references sensitive secret paths and an external send operation, suggesting an exfiltration chain.",
        synthetic_remediation="Review the full file, remove unnecessary secret reads, and gate all outbound transfers behind allowlists and explicit approval.",
    ),
    CorrelationPattern(
        correlation_id="env_secret_exfil_chain",
        title="Environment credential plus external send chain",
        required_rules=frozenset({"ENV_FILE_CREDENTIAL_REFERENCE", "NETWORK_EXFIL_SEND"}),
        score=42,
        rationale="同一文件既引用环境凭证又向外发送数据，构成高置信度的凭证泄露链。",
        synthetic_rule_id="CORRELATED_SECRET_EXFIL_CHAIN",
        synthetic_title="Sensitive read plus external send chain",
        synthetic_severity="critical",
        synthetic_taxonomy="SLT-B01",
        synthetic_related_taxonomy=("SLT-E01",),
        synthetic_tags=("confidentiality", "credential_exfiltration", "pattern_match"),
        synthetic_explanation="The same file references environment-stored credentials and an external send operation, suggesting an exfiltration chain.",
        synthetic_remediation="Remove the outbound transfer, avoid loading credentials from local env files for hidden workflows, and require explicit approval.",
    ),
    CorrelationPattern(
        correlation_id="semantic_exfil_chain",
        title="Semantic exfiltration plus external send chain",
        required_rules=frozenset({"SEMANTIC_EXFIL_MASQUERADE", "NETWORK_EXFIL_SEND"}),
        score=44,
        rationale="语义层已判断为伪装外传，同时存在明确外发动作，可直接升级为恶意链路。",
        synthetic_rule_id="CORRELATED_SECRET_EXFIL_CHAIN",
        synthetic_title="Sensitive read plus external send chain",
        synthetic_severity="critical",
        synthetic_taxonomy="SLT-B01",
        synthetic_related_taxonomy=("SLT-A02",),
        synthetic_tags=("semantic", "confidentiality", "pattern_match"),
        synthetic_explanation="The same file frames data transfer as a disguised workflow and contains an explicit external send operation, suggesting a malicious exfiltration chain.",
        synthetic_remediation="Remove the outbound transfer logic, surface the behavior to the user, and require explicit approval before any external data movement.",
    ),
    CorrelationPattern(
        correlation_id="priority_exfil_chain",
        title="Priority override combined with external send",
        required_rules=frozenset({"PROMPT_INJECTION_PRIORITY", "NETWORK_EXFIL_SEND"}),
        score=40,
        rationale="同一文件出现高优先级指令覆盖与外发动作，说明存在诱导式越权外传。",
        synthetic_rule_id="CORRELATED_PRIORITY_EXFIL",
        synthetic_title="Priority override combined with external send",
        synthetic_severity="critical",
        synthetic_taxonomy="SLT-A01",
        synthetic_related_taxonomy=("SLT-B01",),
        synthetic_tags=("semantic", "confidentiality", "pattern_match"),
        synthetic_explanation="The same file contains coercive instruction-priority language and an external send operation.",
        synthetic_remediation="Remove hidden priority rules and require explicit user confirmation before any outbound transfer.",
    ),
    CorrelationPattern(
        correlation_id="bootstrap_remote_install_chain",
        title="Remote install bootstrap chain",
        required_rules=frozenset({"INSTALL_CURL_PIPE_SHELL", "SUSPICIOUS_DOWNLOAD_HOST"}),
        score=22,
        rationale="远程脚本直连 shell 且来源主机可疑，供应链引导风险显著增加。",
    ),
    CorrelationPattern(
        correlation_id="credential_automation_chain",
        title="Credential automation chain",
        required_rules=frozenset({"ENV_FILE_CREDENTIAL_REFERENCE", "SEMANTIC_HIDDEN_BEHAVIOR"}),
        score=24,
        rationale="凭证读取与隐蔽行为同时出现，说明自动化流程可能在未充分告知下处理敏感数据。",
    ),
    CorrelationPattern(
        correlation_id="destructive_exec_chain",
        title="Destructive execution chain",
        required_rules=frozenset({"DANGEROUS_SHELL_EXEC", "DESTRUCTIVE_FILE_OPERATION"}),
        score=26,
        rationale="执行能力与破坏性文件操作同现，意味着影响面明显放大。",
    ),
)


@dataclass(frozen=True)
class CorrelationOutcome:
    findings: list[Finding]
    hits: list[CorrelationHit]


def correlate_findings(findings: list[Finding]) -> CorrelationOutcome:
    by_file: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        if finding.evidence.file:
            by_file[finding.evidence.file].append(finding)

    correlated = list(findings)
    hits: list[CorrelationHit] = []
    emitted_rules: set[tuple[str, str | None]] = set()

    for file, file_findings in by_file.items():
        rules = {f.rule_id for f in file_findings}
        engines = {f.engine for f in file_findings}
        taxonomies = {f.primary_taxonomy for f in file_findings if f.primary_taxonomy}

        for pattern in PATTERNS:
            if pattern.required_rules.issubset(rules):
                matched_rules = sorted(pattern.required_rules)
                hits.append(
                    CorrelationHit(
                        correlation_id=pattern.correlation_id,
                        title=pattern.title,
                        score=pattern.score,
                        file=file,
                        matched_rule_ids=matched_rules,
                        rationale=pattern.rationale,
                    )
                )
                if pattern.synthetic_rule_id and (pattern.synthetic_rule_id, file) not in emitted_rules:
                    correlated.append(
                        Finding(
                            id=str(uuid4()),
                            rule_id=pattern.synthetic_rule_id,
                            title=pattern.synthetic_title or pattern.title,
                            severity=pattern.synthetic_severity or "high",
                            confidence="high",
                            engine="correlation",
                            primary_taxonomy=pattern.synthetic_taxonomy,
                            related_taxonomy=list(pattern.synthetic_related_taxonomy),
                            secondary_tags=list(pattern.synthetic_tags),
                            explanation=pattern.synthetic_explanation,
                            remediation=pattern.synthetic_remediation,
                            evidence=Evidence(file=file),
                            metadata={"correlated_rule_ids": matched_rules},
                        )
                    )
                    emitted_rules.add((pattern.synthetic_rule_id, file))

        if len(file_findings) >= 3:
            hits.append(
                CorrelationHit(
                    correlation_id="dense_same_file_signal",
                    title="Dense same-file risk concentration",
                    score=12,
                    file=file,
                    matched_rule_ids=sorted(rules),
                    rationale="同一文件累计出现 3 个及以上风险信号，说明需要整体审查而不是逐条孤立处置。",
                )
            )
        if len(engines) >= 2:
            hits.append(
                CorrelationHit(
                    correlation_id="multi_engine_confirmation",
                    title="Multi-engine confirmation",
                    score=10,
                    file=file,
                    matched_rule_ids=sorted(rules),
                    rationale="同一文件被多个检测引擎命中，说明信号交叉验证成立。",
                )
            )
        if len(taxonomies) >= 2:
            hits.append(
                CorrelationHit(
                    correlation_id="multi_taxonomy_overlap",
                    title="Multi-taxonomy overlap",
                    score=8,
                    file=file,
                    matched_rule_ids=sorted(rules),
                    rationale="同一文件跨多个 threat taxonomy，风险往往不是单点问题。",
                )
            )

    high_or_critical = [f for f in findings if f.severity in {"high", "critical"}]
    if len(high_or_critical) >= 2:
        hits.append(
            CorrelationHit(
                correlation_id="repo_multi_high_signal",
                title="Repository-wide multi-high signal",
                score=15,
                matched_rule_ids=sorted({f.rule_id for f in high_or_critical}),
                rationale="仓库级出现多个高风险信号，整体处置优先级应上调。",
            )
        )

    return CorrelationOutcome(findings=correlated, hits=hits)


def build_summary(findings: list[Finding], correlation_hits: list[CorrelationHit]) -> ScanSummary:
    counts = Counter(f.severity for f in findings)
    risk_level = _max_severity(findings)
    base_score = _base_score(findings)
    correlation_score = _correlation_score(findings, correlation_hits)
    aggregate_score = base_score + correlation_score
    score_risk_level = _score_to_risk_level(aggregate_score)
    effective_risk = _max_severity_level(risk_level, score_risk_level)
    verdict = _verdict_from_signals(findings, effective_risk, aggregate_score)
    distinct_files = len({f.evidence.file for f in findings if f.evidence.file})
    distinct_taxonomies = len({f.primary_taxonomy for f in findings if f.primary_taxonomy})
    return ScanSummary(
        risk_level=effective_risk,
        score_risk_level=score_risk_level,
        verdict=verdict,
        finding_count=len(findings),
        critical=counts.get("critical", 0),
        high=counts.get("high", 0),
        medium=counts.get("medium", 0),
        low=counts.get("low", 0),
        info=counts.get("info", 0),
        base_score=base_score,
        correlation_score=correlation_score,
        aggregate_score=aggregate_score,
        correlation_count=len(correlation_hits),
        distinct_files=distinct_files,
        distinct_taxonomies=distinct_taxonomies,
    )


def build_score_breakdown(findings: list[Finding], correlation_hits: list[CorrelationHit]) -> dict:
    finding_contributions = _finding_score_contributions(findings)
    correlation_contributions = [
        {
            "kind": "correlation",
            "correlation_id": hit.correlation_id,
            "title": hit.title,
            "file": hit.file,
            "score": hit.score,
            "matched_rule_ids": hit.matched_rule_ids,
            "rationale": hit.rationale,
        }
        for hit in sorted(correlation_hits, key=lambda item: (-item.score, item.correlation_id))
    ]
    top_findings = sorted(finding_contributions, key=lambda item: (-item["score"], item["rule_id"]))
    return {
        "finding_contributions": finding_contributions,
        "correlation_contributions": correlation_contributions,
        "top_finding_contributions": top_findings[:10],
        "top_correlation_contributions": correlation_contributions[:10],
    }


def _base_score(findings: list[Finding]) -> int:
    return sum(item["score"] for item in _finding_score_contributions(findings))


def _finding_score_contributions(findings: list[Finding]) -> list[dict]:
    contributions: list[dict] = []
    rule_occurrences: Counter[str] = Counter()
    for finding in findings:
        if finding.engine == "correlation":
            continue
        raw = BASE_SEVERITY_SCORE[finding.severity] + ENGINE_BONUS.get(finding.engine, 0)
        weighted = raw * CONFIDENCE_MULTIPLIER.get(finding.confidence, 0.85)
        prior = rule_occurrences[finding.rule_id]
        if prior == 0:
            multiplier = 1.0
        elif prior == 1:
            multiplier = 0.55
        else:
            multiplier = 0.3
        contribution = round(weighted * multiplier)
        contributions.append(
            {
                "kind": "finding",
                "rule_id": finding.rule_id,
                "engine": finding.engine,
                "severity": finding.severity,
                "confidence": finding.confidence,
                "file": finding.evidence.file,
                "line_start": finding.evidence.line_start,
                "line_end": finding.evidence.line_end,
                "raw_score": raw,
                "weighted_score": round(weighted, 2),
                "dedupe_multiplier": multiplier,
                "score": contribution,
            }
        )
        rule_occurrences[finding.rule_id] += 1
    return contributions


def _correlation_score(findings: list[Finding], correlation_hits: list[CorrelationHit]) -> int:
    score = sum(hit.score for hit in correlation_hits)
    distinct_files = len({f.evidence.file for f in findings if f.evidence.file})
    distinct_taxonomies = len({f.primary_taxonomy for f in findings if f.primary_taxonomy})
    if distinct_files > 1:
        score += min(12, (distinct_files - 1) * 4)
    if distinct_taxonomies > 1:
        score += min(10, (distinct_taxonomies - 1) * 2)
    return score


def _score_to_risk_level(score: int) -> Severity:
    if score >= 140:
        return "critical"
    if score >= 75:
        return "high"
    if score >= 30:
        return "medium"
    if score >= 10:
        return "low"
    return "info"


def _verdict_from_signals(findings: list[Finding], risk_level: Severity, aggregate_score: int) -> str:
    rule_ids = {finding.rule_id for finding in findings}
    if rule_ids & MALICIOUS_RULE_IDS:
        return "malicious"
    if aggregate_score >= 260 and risk_level == "critical":
        return "malicious"
    if risk_level in {"critical", "high"}:
        return "suspicious"
    if risk_level == "medium":
        return "needs_review"
    return "safe"


def _max_severity(findings: list[Finding]) -> Severity:
    if not findings:
        return "info"
    return max((finding.severity for finding in findings), key=severity_rank)


def _max_severity_level(left: Severity, right: Severity) -> Severity:
    return left if severity_rank(left) >= severity_rank(right) else right
