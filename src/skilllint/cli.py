from __future__ import annotations

from pathlib import Path

import typer
from rich.console import Console
from rich.table import Table

from skilllint.config import UnknownProfileError, available_profiles, load_config
from skilllint.core.scanner import SkillScanner
from skilllint.evaluation import evaluate_golden_dataset, render_evaluation_markdown
from skilllint.inputs.resolver import resolve_target
from skilllint.reporting.console_renderer import render_console_summary
from skilllint.reporting.json_renderer import render_json
from skilllint.reporting.markdown_renderer import render_markdown
from skilllint.reporting.sarif_renderer import render_sarif

app = typer.Typer(help="SkillLint CLI", no_args_is_help=True)
console = Console()
VALID_FORMATS = {"json", "markdown", "both", "sarif", "all"}


@app.callback()
def main() -> None:
    """SkillLint CLI."""


@app.command("profiles")
def profiles() -> None:
    """List built-in scanning profiles."""
    table = Table(title="SkillLint Profiles")
    table.add_column("Profile")
    table.add_column("Description")
    descriptions = {
        "balanced": "Default profile: package + regex + semantic, dataflow disabled.",
        "strict": "Full local analysis: enables dataflow in addition to baseline engines.",
        "marketplace-review": "Focus on packaging, discovery, supply-chain, and declared-vs-actual mismatch risks.",
        "ci": "Focus on CI/automation workflow hijack, remote instruction loading, and exec abuse.",
    }
    for name in available_profiles():
        table.add_row(name, descriptions.get(name, ""))
    console.print(table)


@app.command("scan")
def scan(
    target: str = typer.Argument(..., help="Path, zip, or URL of the skill"),
    config: Path | None = typer.Option(None, "--config", help="Path to config file"),
    output: Path = typer.Option(Path(".skilllint-out"), "--output", help="Output directory"),
    format: str = typer.Option("both", "--format", help="json|markdown|both|sarif|all"),
    lang: str = typer.Option("auto", "--lang", help="auto|zh|en"),
    profile: str | None = typer.Option(None, "--profile", help="balanced|strict|marketplace-review|ci"),
    enable_rule: list[str] = typer.Option([], "--enable-rule", help="Force-enable a rule ID; repeatable"),
    disable_rule: list[str] = typer.Option([], "--disable-rule", help="Disable a rule ID; repeatable"),
    enable_taxonomy: list[str] = typer.Option([], "--enable-taxonomy", help="Only include findings for a taxonomy code; repeatable"),
    disable_taxonomy: list[str] = typer.Option([], "--disable-taxonomy", help="Exclude a taxonomy code; repeatable"),
    use_llm: bool = typer.Option(
        False,
        "--use-llm",
        help="Enable LLM-based semantic analysis when available",
    ),
    llm_base_url: str | None = typer.Option(
        None,
        "--llm-base-url",
        help="Override SKILLLINT_LLM_BASE_URL for this scan",
    ),
    llm_api_key: str | None = typer.Option(
        None,
        "--llm-api-key",
        help="Override SKILLLINT_LLM_API_KEY for this scan",
    ),
    llm_model: str | None = typer.Option(
        None,
        "--llm-model",
        help="Override SKILLLINT_LLM_MODEL for this scan",
    ),
    llm_debug: bool = typer.Option(
        False,
        "--llm-debug",
        help="Include raw LLM responses in JSON/SARIF metadata for prompt debugging",
    ),
    use_dataflow: bool = typer.Option(
        False,
        "--use-dataflow",
        help="Enable the dataflow engine for Python and shell scripts",
    ),
) -> None:
    if format not in VALID_FORMATS:
        raise typer.BadParameter(f"Unsupported format: {format}. Expected one of: {', '.join(sorted(VALID_FORMATS))}")

    try:
        cfg = load_config(config, profile=profile)
    except UnknownProfileError as exc:
        raise typer.BadParameter(str(exc)) from exc
    cfg.outputs.report_language = lang
    cfg.outputs.format = format
    cfg.engines.semantic.use_llm = use_llm
    if llm_base_url is not None:
        cfg.llm.base_url = llm_base_url
    if llm_api_key is not None:
        cfg.llm.api_key = llm_api_key
    if llm_model is not None:
        cfg.llm.model = llm_model
    if llm_debug:
        cfg.llm.debug = True
    if use_dataflow:
        cfg.engines.dataflow.enabled = True
    cfg.rules.include_rule_ids = sorted({*cfg.rules.include_rule_ids, *enable_rule})
    cfg.rules.exclude_rule_ids = sorted({*cfg.rules.exclude_rule_ids, *disable_rule})
    cfg.rules.include_taxonomies = sorted({*cfg.rules.include_taxonomies, *enable_taxonomy})
    cfg.rules.exclude_taxonomies = sorted({*cfg.rules.exclude_taxonomies, *disable_taxonomy})

    resolved = resolve_target(target)
    if resolved.normalized_type == "unknown":
        raise typer.BadParameter(f"Unsupported target: {target}")

    result = SkillScanner(cfg).scan(resolved)

    output.mkdir(parents=True, exist_ok=True)
    if format in {"json", "both", "all"}:
        render_json(result, output / cfg.outputs.json_file)
    if format in {"markdown", "both", "all"}:
        render_markdown(result, output / cfg.outputs.markdown_file)
    if format in {"sarif", "all"}:
        render_sarif(result, output / cfg.outputs.sarif_file)

    render_console_summary(result)
    console.print(f"[green]Outputs written to[/green] {output}")


@app.command("evaluate-golden")
def evaluate_golden(
    dataset: Path = typer.Option(
        Path("golden/skilllint-golden-subset.yaml"),
        "--dataset",
        help="Path to golden labeled subset YAML",
    ),
    output: Path = typer.Option(
        Path("baselines/golden-eval"),
        "--output",
        help="Output directory for evaluation artifacts",
    ),
    profile: str | None = typer.Option(None, "--profile", help="balanced|strict|marketplace-review|ci"),
    config: Path | None = typer.Option(None, "--config", help="Optional config file override"),
) -> None:
    """Evaluate SkillLint against the golden labeled subset."""
    root = Path.cwd()
    try:
        result = evaluate_golden_dataset(
            root=root,
            dataset_path=dataset,
            profile=profile,
            config_path=config,
        )
    except UnknownProfileError as exc:
        raise typer.BadParameter(str(exc)) from exc

    output.mkdir(parents=True, exist_ok=True)
    json_path = output / "golden-eval.json"
    markdown_path = output / "golden-eval.md"
    json_path.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    markdown_path.write_text(render_evaluation_markdown(result), encoding="utf-8")

    table = Table(title="SkillLint Golden Evaluation")
    table.add_column("Field")
    table.add_column("Value")
    table.add_row("Dataset", str(dataset))
    table.add_row("Profile", result.profile)
    table.add_row("Samples", str(result.sample_count))
    table.add_row("Verdict accuracy", f"{result.verdict_accuracy:.3f}")
    table.add_row("Risk minimum accuracy", f"{result.risk_min_accuracy:.3f}")
    table.add_row("Rule micro F1", f"{result.rule_micro.f1:.3f}")
    table.add_row("Taxonomy micro F1", f"{result.taxonomy_micro.f1:.3f}")
    console.print(table)
    console.print(f"[green]Outputs written to[/green] {output}")


if __name__ == "__main__":
    app()
