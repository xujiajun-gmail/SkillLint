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
    # 统一严重级别排序入口，供 summary、排序、评分等多个模块共享。
    return SEVERITY_ORDER[severity]


class TargetInfo(BaseModel):
    """描述一次扫描输入的“逻辑目标”。

    raw 保存用户原始输入，normalized_type 表示输入归一化后的类型，
    resolved_path 则保存后续 workspace 层真正使用的本地路径或 URL。
    """
    raw: str
    normalized_type: TargetType = "unknown"
    resolved_path: str | None = None


class WorkspaceInfo(BaseModel):
    """描述一次扫描生成的临时工作区。"""
    root_dir: str
    normalized_dir: str
    extracted_from: str | None = None
    source_map: dict[str, str] = Field(default_factory=dict)


class Evidence(BaseModel):
    """描述 finding 的最小证据集。

    SkillLint 尽量把风险定位到文件/行号/片段，便于：
    1. 人类审核；
    2. SARIF/JSON 等下游工具消费；
    3. Web UI 做源码定位与高亮。
    """
    file: str | None = None
    line_start: int | None = None
    line_end: int | None = None
    snippet: str | None = None


class Finding(BaseModel):
    """统一的风险发现模型。

    无论 finding 来源于 regex、semantic、dataflow 还是 correlation，
    最终都被压平成这一种结构，避免报告层与外部集成层按引擎分别适配。
    """
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
    """相关性评分命中记录。

    它与普通 finding 不同：CorrelationHit 主要用于解释“为什么综合评分升高”，
    某些高价值命中还会再派生 synthetic finding 进入最终结果。
    """
    correlation_id: str
    title: str
    score: int
    file: str | None = None
    matched_rule_ids: list[str] = Field(default_factory=list)
    rationale: str | None = None


class ScanSummary(BaseModel):
    """扫描摘要。

    risk_level 偏“离散 finding 视角”，
    score_risk_level 偏“组合评分视角”，
    aggregate_score 则给后续自动化系统一个更容易比较的数值尺度。
    """
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
    """SkillLint 对一次扫描的最终统一输出。"""
    scan_id: str
    tool_version: str
    target: TargetInfo
    workspace: WorkspaceInfo | None = None
    language: ReportLanguage = "en"
    summary: ScanSummary
    findings: list[Finding] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
