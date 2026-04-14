from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

Severity = Literal["info", "low", "medium", "high", "critical"]
Confidence = Literal["low", "medium", "high"]
TargetType = Literal["directory", "zip", "url", "git", "unknown"]
ReportLanguage = Literal["zh", "en"]

SEVERITY_ORDER: dict[Severity, int] = {
    "info": 0,
    "low": 1,
    "medium": 2,
    "high": 3,
    "critical": 4,
}


def severity_rank(severity: Severity) -> int:
    return SEVERITY_ORDER[severity]


class TargetInfo(BaseModel):
    raw: str
    normalized_type: TargetType = "unknown"
    resolved_path: str | None = None


class WorkspaceInfo(BaseModel):
    root_dir: str
    normalized_dir: str
    extracted_from: str | None = None
    source_map: dict[str, str] = Field(default_factory=dict)


class Evidence(BaseModel):
    file: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    snippet: str | None = None


class Finding(BaseModel):
    id: str
    rule_id: str
    title: str
    severity: Severity
    confidence: Confidence = "medium"
    engine: str
    primary_taxonomy: str | None = None
    related_taxonomy: list[str] = Field(default_factory=list)
    secondary_tags: list[str] = Field(default_factory=list)
    explanation: str | None = None
    remediation: str | None = None
    evidence: Evidence = Field(default_factory=Evidence)
    metadata: dict[str, Any] = Field(default_factory=dict)


class CorrelationHit(BaseModel):
    correlation_id: str
    title: str
    score: int
    file: str | None = None
    matched_rule_ids: list[str] = Field(default_factory=list)
    rationale: str | None = None


class ScanSummary(BaseModel):
    risk_level: Severity = "info"
    score_risk_level: Severity = "info"
    verdict: Literal["safe", "suspicious", "malicious", "needs_review"] = "safe"
    finding_count: int = 0
    critical: int = 0
    high: int = 0
    medium: int = 0
    low: int = 0
    info: int = 0
    base_score: int = 0
    correlation_score: int = 0
    aggregate_score: int = 0
    correlation_count: int = 0
    distinct_files: int = 0
    distinct_taxonomies: int = 0


class ScanResult(BaseModel):
    scan_id: str
    tool_version: str
    target: TargetInfo
    workspace: WorkspaceInfo | None = None
    language: ReportLanguage = "en"
    summary: ScanSummary
    findings: list[Finding] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
