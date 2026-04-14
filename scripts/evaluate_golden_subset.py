from __future__ import annotations

import argparse
from pathlib import Path

from skilllint.evaluation import evaluate_golden_dataset, render_evaluation_markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Evaluate SkillLint against the golden labeled subset")
    parser.add_argument("--dataset", default="golden/skilllint-golden-subset.yaml", help="Path to golden dataset YAML")
    parser.add_argument("--profile", default=None, help="Scan profile override")
    parser.add_argument("--config", default=None, help="Optional config path")
    parser.add_argument("--json-out", default="baselines/golden-subset-eval.json", help="JSON output path")
    parser.add_argument("--markdown-out", default="baselines/golden-subset-eval.md", help="Markdown output path")
    args = parser.parse_args()

    root = Path(__file__).resolve().parents[1]
    dataset_path = root / args.dataset
    result = evaluate_golden_dataset(
        root,
        dataset_path,
        profile=args.profile,
        config_path=Path(args.config) if args.config else None,
    )

    json_out = root / args.json_out
    markdown_out = root / args.markdown_out
    json_out.parent.mkdir(parents=True, exist_ok=True)
    markdown_out.parent.mkdir(parents=True, exist_ok=True)
    json_out.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    markdown_out.write_text(render_evaluation_markdown(result), encoding="utf-8")

    print(f"Wrote {json_out}")
    print(f"Wrote {markdown_out}")
    print(f"Verdict accuracy: {result.verdict_accuracy:.3f}")
    print(f"Rule micro F1: {result.rule_micro.f1:.3f}")
    print(f"Taxonomy micro F1: {result.taxonomy_micro.f1:.3f}")


if __name__ == "__main__":
    main()
