from __future__ import annotations

from collections import Counter
from pathlib import Path

from skilllint.models import Finding, ScanResult


def _taxonomy_counter(findings: list[Finding]) -> list[tuple[str, int]]:
    counter = Counter(f.primary_taxonomy or "unmapped" for f in findings)
    return sorted(counter.items(), key=lambda x: (-x[1], x[0]))


def _render_findings_zh(findings: list[Finding]) -> str:
    if not findings:
        return "未发现问题。\n"
    chunks: list[str] = []
    for idx, finding in enumerate(findings, 1):
        ev = finding.evidence
        chunks.extend(
            [
                f"### {idx}. {finding.title}",
                "",
                f"- 规则ID：`{finding.rule_id}`",
                f"- 严重级别：`{finding.severity}`",
                f"- 置信度：`{finding.confidence}`",
                f"- Taxonomy：`{finding.primary_taxonomy or 'unmapped'}`",
                f"- 引擎：`{finding.engine}`",
                f"- 文件：`{ev.file or 'N/A'}`",
                f"- 行号：`{ev.line_start or 'N/A'}` - `{ev.line_end or ev.line_start or 'N/A'}`",
            ]
        )
        if finding.explanation:
            chunks.append(f"- 原因：{finding.explanation}")
        if finding.remediation:
            chunks.append(f"- 建议：{finding.remediation}")
        if ev.snippet:
            chunks.extend(["", "```text", ev.snippet, "```"])
        chunks.append("")
    return "\n".join(chunks)


def _render_findings_en(findings: list[Finding]) -> str:
    if not findings:
        return "No findings were produced.\n"
    chunks: list[str] = []
    for idx, finding in enumerate(findings, 1):
        ev = finding.evidence
        chunks.extend(
            [
                f"### {idx}. {finding.title}",
                "",
                f"- Rule ID: `{finding.rule_id}`",
                f"- Severity: `{finding.severity}`",
                f"- Confidence: `{finding.confidence}`",
                f"- Taxonomy: `{finding.primary_taxonomy or 'unmapped'}`",
                f"- Engine: `{finding.engine}`",
                f"- File: `{ev.file or 'N/A'}`",
                f"- Line: `{ev.line_start or 'N/A'}` - `{ev.line_end or ev.line_start or 'N/A'}`",
            ]
        )
        if finding.explanation:
            chunks.append(f"- Why: {finding.explanation}")
        if finding.remediation:
            chunks.append(f"- Remediation: {finding.remediation}")
        if ev.snippet:
            chunks.extend(["", "```text", ev.snippet, "```"])
        chunks.append("")
    return "\n".join(chunks)


def _render_metadata_lines(result: ScanResult) -> list[str]:
    lines: list[str] = []
    profile = result.metadata.get("profile")
    if profile:
        lines.append(f"- Profile: `{profile}`")
    enabled = result.metadata.get("enabled_engines")
    if enabled:
        lines.append(f"- Enabled engines: `{', '.join(enabled)}`")
    llm_status = result.metadata.get("semantic_llm_status")
    if llm_status and llm_status != "disabled":
        lines.append(f"- Semantic LLM status: `{llm_status}`")
    rule_filters = result.metadata.get("rule_filters") or {}
    for key in ["include_rule_ids", "exclude_rule_ids", "include_taxonomies", "exclude_taxonomies"]:
        values = rule_filters.get(key) or []
        if values:
            lines.append(f"- {key}: `{', '.join(values)}`")
    return lines



def render_markdown(result: ScanResult, path: str | Path) -> None:
    tax_stats = _taxonomy_counter(result.findings)
    if result.language == "zh":
        content = [
            "# SkillLint 扫描报告",
            "",
            f"- 扫描目标：`{result.target.raw}`",
            f"- 输入类型：`{result.target.normalized_type}`",
            f"- 工作区：`{result.workspace.normalized_dir if result.workspace else 'N/A'}`",
            f"- 风险等级：`{result.summary.risk_level}`",
            f"- 结论：`{result.summary.verdict}`",
            f"- Finding 数量：`{result.summary.finding_count}`",
            "",
            "## 风险统计",
            "",
            f"- Critical：{result.summary.critical}",
            f"- High：{result.summary.high}",
            f"- Medium：{result.summary.medium}",
            f"- Low：{result.summary.low}",
            f"- Info：{result.summary.info}",
            "",
            "## Taxonomy 分布",
            "",
        ]
        for code, count in tax_stats:
            content.append(f"- `{code}`: {count}")
        meta_lines = _render_metadata_lines(result)
        if meta_lines:
            content.extend(["", "## 扫描元数据", "", *meta_lines])
        content.extend(["", "## 详细发现", "", _render_findings_zh(result.findings)])
    else:
        content = [
            "# SkillLint Scan Report",
            "",
            f"- Target: `{result.target.raw}`",
            f"- Input type: `{result.target.normalized_type}`",
            f"- Workspace: `{result.workspace.normalized_dir if result.workspace else 'N/A'}`",
            f"- Risk level: `{result.summary.risk_level}`",
            f"- Verdict: `{result.summary.verdict}`",
            f"- Findings: `{result.summary.finding_count}`",
            "",
            "## Severity Summary",
            "",
            f"- Critical: {result.summary.critical}",
            f"- High: {result.summary.high}",
            f"- Medium: {result.summary.medium}",
            f"- Low: {result.summary.low}",
            f"- Info: {result.summary.info}",
            "",
            "## Taxonomy Distribution",
            "",
        ]
        for code, count in tax_stats:
            content.append(f"- `{code}`: {count}")
        meta_lines = _render_metadata_lines(result)
        if meta_lines:
            content.extend(["", "## Scan Metadata", "", *meta_lines])
        content.extend(["", "## Detailed Findings", "", _render_findings_en(result.findings)])
    Path(path).write_text("\n".join(content).strip() + "\n", encoding="utf-8")
