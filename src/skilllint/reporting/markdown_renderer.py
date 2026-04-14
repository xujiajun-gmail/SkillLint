from __future__ import annotations

from collections import Counter
from pathlib import Path

from skilllint.models import Finding, ScanResult


def _taxonomy_counter(findings: list[Finding]) -> list[tuple[str, int]]:
    counter = Counter(f.primary_taxonomy or "unmapped" for f in findings)
    return sorted(counter.items(), key=lambda x: (-x[1], x[0]))


def _top_findings(findings: list[Finding], limit: int = 5) -> list[Finding]:
    return sorted(findings, key=lambda f: (_severity_score(f.severity), f.rule_id), reverse=True)[:limit]


def _severity_score(value: str) -> int:
    order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    return order.get(value, 0)


def _severity_badge(value: str) -> str:
    icons = {
        "critical": "🔴 critical",
        "high": "🟠 high",
        "medium": "🟡 medium",
        "low": "🔵 low",
        "info": "⚪ info",
    }
    return icons.get(value, value)


def _md_table(headers: list[str], rows: list[list[str]]) -> list[str]:
    # 使用纯 Markdown 表格而不是模板引擎，保持输出简单、可预测、易测试。
    lines = [
        "| " + " | ".join(headers) + " |",
        "| " + " | ".join(["---"] * len(headers)) + " |",
    ]
    for row in rows:
        safe = [cell.replace("\n", "<br>") for cell in row]
        lines.append("| " + " | ".join(safe) + " |")
    return lines


def _top_findings_table_rows(findings: list[Finding]) -> list[list[str]]:
    rows: list[list[str]] = []
    for finding in _top_findings(findings):
        rows.append(
            [
                f"`{finding.rule_id}`",
                f"`{finding.severity}`",
                f"`{finding.primary_taxonomy or 'unmapped'}`",
                f"`{finding.evidence.file or 'N/A'}`",
                finding.title,
            ]
        )
    return rows


def _summary_rows(result: ScanResult, zh: bool) -> list[list[str]]:
    if zh:
        return [
            ["目标", f"`{result.target.raw}`"],
            ["输入类型", f"`{result.target.normalized_type}`"],
            ["结论", f"`{result.summary.verdict}`"],
            ["风险等级", f"`{result.summary.risk_level}`"],
            ["评分风险等级", f"`{result.summary.score_risk_level}`"],
            ["发现数量", str(result.summary.finding_count)],
            ["聚合分数", str(result.summary.aggregate_score)],
            ["相关性命中", str(result.summary.correlation_count)],
            ["涉及文件", str(result.summary.distinct_files)],
            ["涉及 taxonomy", str(result.summary.distinct_taxonomies)],
        ]
    return [
        ["Target", f"`{result.target.raw}`"],
        ["Input type", f"`{result.target.normalized_type}`"],
        ["Verdict", f"`{result.summary.verdict}`"],
        ["Risk level", f"`{result.summary.risk_level}`"],
        ["Score risk level", f"`{result.summary.score_risk_level}`"],
        ["Findings", str(result.summary.finding_count)],
        ["Aggregate score", str(result.summary.aggregate_score)],
        ["Correlation hits", str(result.summary.correlation_count)],
        ["Distinct files", str(result.summary.distinct_files)],
        ["Distinct taxonomies", str(result.summary.distinct_taxonomies)],
    ]


def _severity_rows(result: ScanResult) -> list[list[str]]:
    return [
        ["critical", str(result.summary.critical)],
        ["high", str(result.summary.high)],
        ["medium", str(result.summary.medium)],
        ["low", str(result.summary.low)],
        ["info", str(result.summary.info)],
    ]


def _taxonomy_rows(findings: list[Finding]) -> list[list[str]]:
    return [[f"`{code}`", str(count)] for code, count in _taxonomy_counter(findings)]


def _finding_detail_rows(finding: Finding, zh: bool) -> list[list[str]]:
    ev = finding.evidence
    line_value = f"`{ev.line_start or 'N/A'}` - `{ev.line_end or ev.line_start or 'N/A'}`"
    base = [
        ["规则ID" if zh else "Rule ID", f"`{finding.rule_id}`"],
        ["严重级别" if zh else "Severity", f"`{finding.severity}`"],
        ["置信度" if zh else "Confidence", f"`{finding.confidence}`"],
        ["Taxonomy", f"`{finding.primary_taxonomy or 'unmapped'}`"],
        ["引擎" if zh else "Engine", f"`{finding.engine}`"],
        ["文件" if zh else "File", f"`{ev.file or 'N/A'}`"],
        ["行号" if zh else "Line range", line_value],
    ]
    if finding.related_taxonomy:
        base.append(
            [
                "关联 taxonomy" if zh else "Related taxonomy",
                ", ".join(f"`{item}`" for item in finding.related_taxonomy),
            ]
        )
    if finding.secondary_tags:
        base.append(
            [
                "标签" if zh else "Tags",
                ", ".join(f"`{item}`" for item in finding.secondary_tags),
            ]
        )
    return base


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
                f"> 风险：**{_severity_badge(finding.severity)}**",
                "",
                *_md_table(["字段", "值"], _finding_detail_rows(finding, zh=True)),
            ]
        )
        if finding.explanation:
            chunks.extend(["", f"**原因**：{finding.explanation}"])
        if finding.remediation:
            chunks.extend(["", f"**建议**：{finding.remediation}"])
        if ev.snippet:
            chunks.extend(["", "**证据片段**", "", "```text", ev.snippet, "```"])
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
                f"> Risk: **{_severity_badge(finding.severity)}**",
                "",
                *_md_table(["Field", "Value"], _finding_detail_rows(finding, zh=False)),
            ]
        )
        if finding.explanation:
            chunks.extend(["", f"**Why**: {finding.explanation}"])
        if finding.remediation:
            chunks.extend(["", f"**Remediation**: {finding.remediation}"])
        if ev.snippet:
            chunks.extend(["", "**Evidence snippet**", "", "```text", ev.snippet, "```"])
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


def _render_correlation_hits(result: ScanResult) -> list[str]:
    hits = result.metadata.get("correlation_hits") or []
    if not hits:
        return []
    lines = []
    for hit in hits:
        matched = ", ".join(hit.get("matched_rule_ids") or []) or "N/A"
        location = hit.get("file") or "repository"
        rationale = hit.get("rationale") or ""
        lines.extend(
            [
                f"- `{hit['correlation_id']}` (+{hit['score']}) @ `{location}`",
                f"  - matched_rules: `{matched}`",
                f"  - rationale: {rationale}",
            ]
        )
    return lines


def _render_score_drivers(result: ScanResult) -> list[str]:
    breakdown = result.metadata.get("score_breakdown") or {}
    finding_items = breakdown.get("top_finding_contributions") or []
    correlation_items = breakdown.get("top_correlation_contributions") or []
    if not finding_items and not correlation_items:
        return []
    lines: list[str] = []
    if finding_items:
        lines.append("### Top finding contributions")
        lines.append("")
        for item in finding_items:
            location = item.get("file") or "repository"
            lines.append(
                f"- `{item['rule_id']}` +{item['score']} @ `{location}` "
                f"({item['engine']}/{item['severity']}/{item['confidence']})"
            )
        lines.append("")
    if correlation_items:
        lines.append("### Top correlation contributions")
        lines.append("")
        for item in correlation_items:
            location = item.get("file") or "repository"
            lines.append(f"- `{item['correlation_id']}` +{item['score']} @ `{location}`")
        lines.append("")
    return lines



def render_markdown(result: ScanResult, path: str | Path) -> None:
    """把统一 ScanResult 渲染成人类可读的 Markdown 报告。"""
    correlation_lines = _render_correlation_hits(result)
    score_driver_lines = _render_score_drivers(result)
    if result.language == "zh":
        content = [
            "# SkillLint 扫描报告",
            "",
            "## 总览",
            "",
            *_md_table(["字段", "值"], _summary_rows(result, zh=True)),
            "",
            f"> 工作区：`{result.workspace.normalized_dir if result.workspace else 'N/A'}`",
            "",
            "## 风险统计",
            "",
            *_md_table(["严重级别", "数量"], _severity_rows(result)),
            "",
            "## Taxonomy 分布",
            "",
            *_md_table(["Taxonomy", "数量"], _taxonomy_rows(result.findings) or [["`unmapped`", "0"]]),
        ]
        top_rows = _top_findings_table_rows(result.findings)
        if top_rows:
            content.extend(["", "## 重点发现", "", *_md_table(["Rule ID", "Severity", "Taxonomy", "文件", "标题"], top_rows)])
        meta_lines = _render_metadata_lines(result)
        if meta_lines:
            content.extend(["", "## 扫描元数据", "", *meta_lines])
        if correlation_lines:
            content.extend(["", "## 相关性加权命中", "", *correlation_lines])
        if score_driver_lines:
            content.extend(["", "## 评分驱动因素", "", *score_driver_lines])
        content.extend(["", "## 详细发现", "", _render_findings_zh(result.findings)])
    else:
        content = [
            "# SkillLint Scan Report",
            "",
            "## Overview",
            "",
            *_md_table(["Field", "Value"], _summary_rows(result, zh=False)),
            "",
            f"> Workspace: `{result.workspace.normalized_dir if result.workspace else 'N/A'}`",
            "",
            "## Severity Summary",
            "",
            *_md_table(["Severity", "Count"], _severity_rows(result)),
            "",
            "## Taxonomy Distribution",
            "",
            *_md_table(["Taxonomy", "Count"], _taxonomy_rows(result.findings) or [["`unmapped`", "0"]]),
        ]
        top_rows = _top_findings_table_rows(result.findings)
        if top_rows:
            content.extend(
                [
                    "",
                    "## Top Findings",
                    "",
                    *_md_table(["Rule ID", "Severity", "Taxonomy", "File", "Title"], top_rows),
                ]
            )
        meta_lines = _render_metadata_lines(result)
        if meta_lines:
            content.extend(["", "## Scan Metadata", "", *meta_lines])
        if correlation_lines:
            content.extend(["", "## Correlation Hits", "", *correlation_lines])
        if score_driver_lines:
            content.extend(["", "## Score Drivers", "", *score_driver_lines])
        content.extend(["", "## Detailed Findings", "", _render_findings_en(result.findings)])
    Path(path).write_text("\n".join(content).strip() + "\n", encoding="utf-8")
