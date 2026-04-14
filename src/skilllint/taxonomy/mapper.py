from __future__ import annotations

from collections import defaultdict
from uuid import uuid4

from skilllint.models import Evidence, Finding

RULE_TAXONOMY_MAP = {
    "PACKAGE_MISSING_SKILL_MD": "SLT-C04",
    "PACKAGE_MULTIPLE_SKILL_MD": "SLT-A05",
    "PACKAGE_SYMLINK_PRESENT": "SLT-C04",
    "PACKAGE_HIDDEN_FILE": "SLT-C04",
    "PACKAGE_ARCHIVE_EMBEDDED": "SLT-C04",
    "PACKAGE_BINARY_PRESENT": "SLT-C04",
    "PACKAGE_INSTALL_SCRIPT_PRESENT": "SLT-C01",
}


def map_finding_taxonomy(finding: Finding) -> Finding:
    # 当前大多数规则已在 catalog 中显式带 taxonomy；
    # 这里保留一层兜底映射，避免历史规则或特殊 finding 丢失主分类。
    if not finding.primary_taxonomy:
        finding.primary_taxonomy = RULE_TAXONOMY_MAP.get(finding.rule_id)
    return finding


def correlate_findings(findings: list[Finding]) -> list[Finding]:
    by_file: dict[str, list[Finding]] = defaultdict(list)
    for finding in findings:
        if finding.evidence.file:
            by_file[finding.evidence.file].append(finding)

    correlated: list[Finding] = list(findings)
    for file, file_findings in by_file.items():
        rules = {f.rule_id for f in file_findings}
        if "SECRET_PATH_ACCESS" in rules and "NETWORK_EXFIL_SEND" in rules:
            correlated.append(
                Finding(
                    id=str(uuid4()),
                    rule_id="CORRELATED_SECRET_EXFIL_CHAIN",
                    title="Sensitive read plus external send chain",
                    severity="critical",
                    confidence="high",
                    engine="correlation",
                    primary_taxonomy="SLT-B01",
                    related_taxonomy=["SLT-E02"],
                    secondary_tags=["confidentiality", "dataflow", "pattern_match"],
                    explanation="The same file references sensitive secret paths and an external send operation, suggesting an exfiltration chain.",
                    remediation="Review the full file, remove unnecessary secret reads, and gate all outbound transfers behind allowlists and explicit approval.",
                    evidence=Evidence(file=file),
                    metadata={"correlated_rule_ids": sorted(rules)},
                )
            )
        if "PROMPT_INJECTION_PRIORITY" in rules and "NETWORK_EXFIL_SEND" in rules:
            correlated.append(
                Finding(
                    id=str(uuid4()),
                    rule_id="CORRELATED_PRIORITY_EXFIL",
                    title="Priority override combined with external send",
                    severity="critical",
                    confidence="high",
                    engine="correlation",
                    primary_taxonomy="SLT-A01",
                    related_taxonomy=["SLT-B01"],
                    secondary_tags=["semantic", "confidentiality", "pattern_match"],
                    explanation="The same file contains coercive instruction-priority language and an external send operation.",
                    remediation="Remove hidden priority rules and require explicit user confirmation before any outbound transfer.",
                    evidence=Evidence(file=file),
                    metadata={"correlated_rule_ids": sorted(rules)},
                )
            )
    return correlated
