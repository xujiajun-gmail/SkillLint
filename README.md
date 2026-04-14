# SkillLint

SkillLint is a security scanner for agent skills.

## Goals

SkillLint is being built as a CLI-first tool that can scan a skill from:
- a local directory
- a zip archive
- a remote URL
- a git repository URL

It is intended to produce:
- machine-readable results for downstream tooling
- a detailed human-readable report
- taxonomy-based security classification
- file or line-level evidence whenever possible

## Current status

### Research & design
- Security research report: `docs/skill-security-threat-research-report.md`
- Formal threat taxonomy: `docs/skilllint-threat-taxonomy.md`
- CLI development plan: `docs/skilllint-cli-development-plan.md`
- Rule catalog: `docs/skilllint-rule-catalog.md`
- Profiles and rule filters: `docs/skilllint-profiles.md`
- SARIF output: `docs/skilllint-sarif-output.md`
- Example baseline snapshot: `docs/skilllint-example-baseline.md`
- Golden labeled subset and evaluation: `docs/skilllint-golden-evaluation.md`
- Correlation scoring: `docs/skilllint-correlation-scoring.md`
- False-positive triage round 1: `docs/skilllint-fp-triage-round1.md`
- False-positive triage round 2: `docs/skilllint-fp-triage-round2.md`
- False-positive triage round 3: `docs/skilllint-fp-triage-round3.md`
- False-positive triage round 4: `docs/skilllint-fp-triage-round4.md`

### Sample collections
- General examples: `examples/`
- Chinese community examples: `examples/zh-community/`

### Implemented in the current baseline
- Python package scaffold
- `skilllint scan <target>` CLI entrypoint
- built-in scan profiles: `balanced`, `strict`, `marketplace-review`, `ci`
- rule filtering by `rule_id` and taxonomy
- target type resolution: directory / zip / URL / git URL
- workspace normalization
- package engine
- regex engine
- semantic engine (local heuristics + optional LLM review)
- dataflow engine (Python AST + shell heuristics, opt-in or via profile)
- structured rule catalog under `src/skilllint/rules/`
- taxonomy mapping and finding correlation
- golden labeled subset for regression evaluation
- precision/recall-style rule and taxonomy evaluation
- aggregate correlation scoring in scan summaries
- JSON output
- Markdown report with auto Chinese or English selection
- SARIF 2.1.0 output
- console summary

### Not implemented yet
- richer LLM semantic workflows (multi-pass triage / consensus / budget policies)
- advanced reputation / cross-skill analysis
- external custom rule packs
- deeper SARIF taxonomy component modeling

## Quick start

```bash
pip install -e .[dev]
skilllint scan ./examples/openai/playwright --output .skilllint-out
```

You can also scan a zip or URL:

```bash
skilllint scan ./skill.zip
skilllint scan https://example.com/skill.zip
skilllint scan https://github.com/openai/skills
```

## CLI

```bash
skilllint scan <target> \
  --profile balanced \
  --format both \
  --output .skilllint-out \
  --lang auto
```

Optional deeper analysis:

```bash
skilllint scan <target> --profile strict
skilllint scan <target> --use-dataflow
skilllint scan <target> --use-llm
```

Profile discovery:

```bash
skilllint profiles
```

Rule and taxonomy filtering:

```bash
skilllint scan <target> --disable-rule PROMPT_INJECTION_PRIORITY
skilllint scan <target> --enable-taxonomy SLT-D01
```

SARIF output:

```bash
skilllint scan <target> --format sarif
skilllint scan <target> --format all
```

Golden subset evaluation:

```bash
skilllint evaluate-golden
skilllint evaluate-golden --profile balanced --output baselines/golden-eval
```

## Repository layout

```text
config/
docs/
examples/
scripts/
src/skilllint/
tests/
```

## Detection engines

SkillLint currently combines four engine families:
- `package`: package structure, symlink, archive, binary, startup artifact, workflow presence
- `regex`: high-confidence signatures for prompt injection, exfil, install abuse, persistence, destructive actions
- `semantic`: keyword-group and heuristic semantic analysis, plus optional LLM-assisted review
- `dataflow`: source-to-sink analysis for Python helpers and shell scripts

## Rule catalog

Structured rules now live in:

```text
src/skilllint/rules/
├── regex/rules.yaml
├── package/rules.yaml
├── semantic/rules.yaml
└── dataflow/rules.yaml
```

The scanner exposes rule metadata in findings, and scan metadata includes current catalog counts, active profile, enabled engines, and active rule filters.

## Outputs

SkillLint currently supports:
- JSON
- Markdown
- SARIF 2.1.0

Scan outputs now also include correlation hits and score-breakdown metadata for explainability.

## Baselines

Example corpus baseline artifacts live under `baselines/` and can be regenerated with:

```bash
python3 scripts/generate_example_baseline.py
```

Golden subset evaluation artifacts can be regenerated with:

```bash
python3 scripts/evaluate_golden_subset.py
```

The current shipped golden subset is a larger strict-profile adjudicated set with stronger
coverage for zh-community skills, packaging risks, CI risks, and dataflow cases.

## License

Apache-2.0
