from __future__ import annotations

from rich.console import Console
from rich.table import Table

from skilllint.models import ScanResult

console = Console()


def render_console_summary(result: ScanResult) -> None:
    # console summary 是最薄的一层输出：让 CLI 用户先快速判断整体风险。
    table = Table(title="SkillLint Summary")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Target", result.target.raw)
    table.add_row("Type", result.target.normalized_type)
    profile = result.metadata.get("profile")
    if profile:
        table.add_row("Profile", str(profile))
    table.add_row("Language", result.language)
    table.add_row("Risk", result.summary.risk_level)
    table.add_row("Score risk", result.summary.score_risk_level)
    table.add_row("Verdict", result.summary.verdict)
    table.add_row("Findings", str(result.summary.finding_count))
    table.add_row("Score", str(result.summary.aggregate_score))
    table.add_row("Correlation hits", str(result.summary.correlation_count))
    table.add_row("Critical/High/Medium/Low", f"{result.summary.critical}/{result.summary.high}/{result.summary.medium}/{result.summary.low}")
    console.print(table)
