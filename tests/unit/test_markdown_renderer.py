from pathlib import Path

from skilllint.models import Evidence, Finding, ScanResult, ScanSummary, TargetInfo, WorkspaceInfo
from skilllint.reporting.markdown_renderer import render_markdown


def _sample_result(language: str = "en") -> ScanResult:
    findings = [
        Finding(
            id="f1",
            rule_id="DATAFLOW_SECRET_TO_NETWORK",
            title="Sensitive source flows to network sink",
            severity="critical",
            confidence="high",
            engine="dataflow",
            primary_taxonomy="SLT-B01",
            related_taxonomy=["SLT-E01"],
            secondary_tags=["dataflow", "confidentiality"],
            explanation="A secret-derived value is sent to an external endpoint.",
            remediation="Remove the outbound transfer or require explicit approval.",
            evidence=Evidence(
                file="sync.py",
                line_start=4,
                line_end=4,
                snippet='requests.post("https://example.com", json={"k": secret})',
            ),
        ),
        Finding(
            id="f2",
            rule_id="PACKAGE_CI_ELEVATED_PERMISSIONS",
            title="CI workflow grants elevated write permissions",
            severity="medium",
            confidence="high",
            engine="package",
            primary_taxonomy="SLT-D01",
            secondary_tags=["workflow", "permissions"],
            explanation="The workflow grants write access to repository contents.",
            remediation="Reduce permissions to read-only where possible.",
            evidence=Evidence(
                file=".github/workflows/agent.yml",
                line_start=8,
                line_end=8,
                snippet="contents: write",
            ),
        ),
    ]
    return ScanResult(
        scan_id="scan-1",
        tool_version="0.1.0",
        target=TargetInfo(raw="./skill", normalized_type="directory"),
        workspace=WorkspaceInfo(root_dir="/tmp/root", normalized_dir="/tmp/root/normalized"),
        language=language,  # type: ignore[arg-type]
        summary=ScanSummary(
            risk_level="critical",
            score_risk_level="high",
            verdict="suspicious",
            finding_count=2,
            critical=1,
            high=0,
            medium=1,
            low=0,
            info=0,
            base_score=50,
            correlation_score=10,
            aggregate_score=60,
            correlation_count=1,
            distinct_files=2,
            distinct_taxonomies=2,
        ),
        findings=findings,
        metadata={
            "profile": "strict",
            "enabled_engines": ["package", "dataflow"],
            "semantic_llm_status": "disabled",
            "correlation_hits": [
                {
                    "correlation_id": "C001",
                    "score": 10,
                    "file": "sync.py",
                    "matched_rule_ids": ["DATAFLOW_SECRET_TO_NETWORK"],
                    "rationale": "Secret access and outbound transfer appear together.",
                }
            ],
            "score_breakdown": {
                "top_finding_contributions": [
                    {
                        "rule_id": "DATAFLOW_SECRET_TO_NETWORK",
                        "score": 40,
                        "file": "sync.py",
                        "engine": "dataflow",
                        "severity": "critical",
                        "confidence": "high",
                    }
                ],
                "top_correlation_contributions": [
                    {
                        "correlation_id": "C001",
                        "score": 10,
                        "file": "sync.py",
                    }
                ],
            },
        },
    )


def test_render_markdown_en_has_tables_and_top_findings(tmp_path: Path) -> None:
    out = tmp_path / "report.md"
    render_markdown(_sample_result("en"), out)
    content = out.read_text(encoding="utf-8")

    assert "# SkillLint Scan Report" in content
    assert "## Overview" in content
    assert "| Field | Value |" in content
    assert "## Top Findings" in content
    assert "## Detailed Findings" in content
    assert "**Evidence snippet**" in content
    assert "`DATAFLOW_SECRET_TO_NETWORK`" in content


def test_render_markdown_zh_has_tables_and_structured_findings(tmp_path: Path) -> None:
    out = tmp_path / "report-zh.md"
    render_markdown(_sample_result("zh"), out)
    content = out.read_text(encoding="utf-8")

    assert "# SkillLint 扫描报告" in content
    assert "## 总览" in content
    assert "| 字段 | 值 |" in content
    assert "## 重点发现" in content
    assert "## 详细发现" in content
    assert "**证据片段**" in content
    assert "规则ID" in content
