#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

from skilllint.baseline import build_baseline_dataset, render_baseline_markdown

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_JSON = ROOT / 'baselines' / 'examples-balanced-baseline.json'
DEFAULT_MD = ROOT / 'docs' / 'skilllint-example-baseline.md'


def main() -> None:
    parser = argparse.ArgumentParser(description='Generate SkillLint baseline data for examples corpus.')
    parser.add_argument('--profile', default='balanced', help='SkillLint profile to use')
    parser.add_argument('--config', type=Path, default=None, help='Optional config file')
    parser.add_argument('--json-out', type=Path, default=DEFAULT_JSON, help='Output JSON path')
    parser.add_argument('--md-out', type=Path, default=DEFAULT_MD, help='Output Markdown path')
    args = parser.parse_args()

    dataset = build_baseline_dataset(ROOT, profile=args.profile, config_path=args.config)

    args.json_out.parent.mkdir(parents=True, exist_ok=True)
    args.md_out.parent.mkdir(parents=True, exist_ok=True)
    args.json_out.write_text(json.dumps(dataset, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    args.md_out.write_text(render_baseline_markdown(dataset), encoding='utf-8')

    print(f"Wrote baseline JSON to {args.json_out}")
    print(f"Wrote baseline Markdown to {args.md_out}")
    print(f"Scanned samples: {dataset['sample_count']}")
    print(f"Failures: {dataset['failure_count']}")


if __name__ == '__main__':
    main()
