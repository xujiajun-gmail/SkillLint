from __future__ import annotations

import json
from pathlib import Path

from skilllint.models import Finding, ScanResult

SARIF_VERSION = "2.1.0"
SARIF_SCHEMA = (
    "https://json.schemastore.org/sarif-2.1.0.json"
)


LEVEL_MAP = {
    "critical": "error",
    "high": "error",
    "medium": "warning",
    "low": "note",
    "info": "note",
}

PRECISION_MAP = {
    "high": "very-high",
    "medium": "high",
    "low": "medium",
}


def render_sarif(result: ScanResult, path: str | Path) -> None:
    sarif = build_sarif_log(result)
    Path(path).write_text(json.dumps(sarif, indent=2), encoding="utf-8")


def build_sarif_log(result: ScanResult) -> dict:
    rules = [_rule_to_sarif(rule_id, group) for rule_id, group in _group_findings_by_rule(result.findings).items()]
    sarif_results = [_finding_to_sarif(finding) for finding in result.findings]

    run = {
        "tool": {
            "driver": {
                "name": "SkillLint",
                "version": result.tool_version,
                "informationUri": "https://github.com/xujiajun-gmail/SkillLint",
                "rules": rules,
            }
        },
        "automationDetails": {
            "id": result.scan_id,
        },
        "invocations": [
            {
                "executionSuccessful": True,
                "toolExecutionNotifications": [],
            }
        ],
        "properties": {
            "target": result.target.raw,
            "target_type": result.target.normalized_type,
            "profile": result.metadata.get("profile"),
            "language": result.language,
            "summary": result.summary.model_dump(),
            "enabled_engines": result.metadata.get("enabled_engines", []),
            "rule_filters": result.metadata.get("rule_filters", {}),
            "correlation_hits": result.metadata.get("correlation_hits", []),
            "score_breakdown": result.metadata.get("score_breakdown", {}),
        },
        "results": sarif_results,
        "originalUriBaseIds": {
            "SOURCE_ROOT": {
                "uri": _source_root_uri(result),
            }
        },
    }

    return {
        "$schema": SARIF_SCHEMA,
        "version": SARIF_VERSION,
        "runs": [run],
    }


def _group_findings_by_rule(findings: list[Finding]) -> dict[str, list[Finding]]:
    grouped: dict[str, list[Finding]] = {}
    for finding in findings:
        grouped.setdefault(finding.rule_id, []).append(finding)
    return grouped


def _rule_to_sarif(rule_id: str, findings: list[Finding]) -> dict:
    exemplar = findings[0]
    short_description = exemplar.title
    full_description = exemplar.explanation or exemplar.title
    help_text = exemplar.remediation or "Review this finding and validate whether the behavior is expected."
    tags = [exemplar.engine, exemplar.severity, exemplar.confidence]
    if exemplar.primary_taxonomy:
        tags.append(exemplar.primary_taxonomy)
    tags.extend(exemplar.secondary_tags)
    related = sorted({code for finding in findings for code in finding.related_taxonomy if code})
    if related:
        tags.extend(related)
    return {
        "id": rule_id,
        "name": exemplar.title,
        "shortDescription": {"text": short_description},
        "fullDescription": {"text": full_description},
        "help": {
            "text": help_text,
            "markdown": _rule_help_markdown(exemplar, related),
        },
        "defaultConfiguration": {
            "level": LEVEL_MAP.get(exemplar.severity, "warning"),
        },
        "properties": {
            "precision": PRECISION_MAP.get(exemplar.confidence, "high"),
            "tags": sorted(dict.fromkeys(tags)),
            "taxonomy": exemplar.primary_taxonomy,
            "related_taxonomy": related,
            "engine": exemplar.engine,
            "severity": exemplar.severity,
            "confidence": exemplar.confidence,
        },
    }


def _rule_help_markdown(exemplar: Finding, related: list[str]) -> str:
    lines = [f"**Taxonomy:** `{exemplar.primary_taxonomy or 'unmapped'}`"]
    if related:
        lines.append(f"**Related taxonomy:** `{', '.join(related)}`")
    if exemplar.explanation:
        lines.append("")
        lines.append(exemplar.explanation)
    if exemplar.remediation:
        lines.append("")
        lines.append(f"**Remediation:** {exemplar.remediation}")
    return "\n".join(lines)


def _finding_to_sarif(finding: Finding) -> dict:
    level = LEVEL_MAP.get(finding.severity, "warning")
    message = finding.explanation or finding.title
    result = {
        "ruleId": finding.rule_id,
        "level": level,
        "message": {"text": message},
        "properties": {
            "severity": finding.severity,
            "confidence": finding.confidence,
            "engine": finding.engine,
            "taxonomy": finding.primary_taxonomy,
            "related_taxonomy": finding.related_taxonomy,
            "tags": finding.secondary_tags,
            "skilllint_finding_id": finding.id,
            **finding.metadata,
        },
        "partialFingerprints": {
            "primaryLocationLineHash": _fingerprint(finding),
        },
    }
    location = _location_from_finding(finding)
    if location is not None:
        result["locations"] = [location]
    if finding.remediation:
        result["fixes"] = [
            {
                "description": {"text": finding.remediation},
            }
        ]
    return result


def _location_from_finding(finding: Finding) -> dict | None:
    if not finding.evidence.file:
        return None
    region = {}
    if finding.evidence.line_start is not None:
        region["startLine"] = finding.evidence.line_start
    if finding.evidence.line_end is not None:
        region["endLine"] = finding.evidence.line_end
    if finding.evidence.snippet:
        region["snippet"] = {"text": finding.evidence.snippet}
    physical_location = {
        "artifactLocation": {
            "uri": finding.evidence.file,
            "uriBaseId": "SOURCE_ROOT",
        }
    }
    if region:
        physical_location["region"] = region
    return {
        "physicalLocation": physical_location,
    }


def _fingerprint(finding: Finding) -> str:
    parts = [
        finding.rule_id,
        finding.evidence.file or "",
        str(finding.evidence.line_start or ""),
        str(finding.evidence.line_end or ""),
        finding.evidence.snippet or "",
    ]
    return "|".join(parts)


def _source_root_uri(result: ScanResult) -> str:
    if result.workspace is None:
        return "file:///"
    normalized = Path(result.workspace.normalized_dir).resolve()
    return normalized.as_uri().rstrip("/") + "/"
