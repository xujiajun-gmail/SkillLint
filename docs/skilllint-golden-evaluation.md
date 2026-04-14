# SkillLint Golden Labeled Subset & Evaluation

SkillLint now includes a curated golden labeled subset for regression testing:

- Dataset: `golden/skilllint-golden-subset.yaml`
- Synthetic fixtures: `golden/fixtures/`
- Evaluation script: `scripts/evaluate_golden_subset.py`
- Latest outputs:
  - `baselines/golden-subset-eval.json`
  - `baselines/golden-subset-eval.md`

## Goals

This subset is designed to support three things simultaneously:

1. **Sample-level verdict regression**
2. **Rule-level precision / recall style measurement**
3. **Taxonomy-level precision / recall style measurement**

It intentionally mixes:

- public real-world skills from `examples/`
- Chinese community skills from `examples/zh-community/`
- a small number of synthetic fixtures for high-confidence malicious and negative-control cases
- package / CI / dataflow / regex / semantic focused synthetic fixtures for engine coverage

## Dataset Schema

Each sample currently supports:

- `sample_id`
- `local_path`
- `source_alias`
- `community`
- `expected_verdict`
- `expected_min_risk`
- `expected_rules_present`
- `expected_rules_absent`
- `expected_taxonomies_present`
- `expected_taxonomies_absent`
- `rationale`
- `notes`

Important: rule/taxonomy labels are **partial labels**.
Unlabeled rules are treated as unknown and excluded from PR-style metrics.

## How to Run

```bash
python3 scripts/evaluate_golden_subset.py
```

Or via the CLI:

```bash
skilllint evaluate-golden
```

Optional overrides:

```bash
python3 scripts/evaluate_golden_subset.py \
  --dataset golden/skilllint-golden-subset.yaml \
  --profile balanced \
  --json-out baselines/golden-subset-eval.json \
  --markdown-out baselines/golden-subset-eval.md
```

## Current Snapshot

Latest strict-profile snapshot:

- sample_count: `71`
- verdict_accuracy: `1.000`
- risk_min_accuracy: `1.000`
- rule_micro_f1: `1.000`
- taxonomy_micro_f1: `1.000`

See `baselines/golden-subset-eval.md` for the detailed mismatch report and per-rule metrics.

## Adjudication Guidance

When expanding the subset:

- prefer high-confidence labels over larger volume
- record only rules/taxonomies you are confident should be present or absent
- preserve hard negative samples for historically noisy rules
- preserve high-signal malicious chains for correlation regression
- keep zh/en coverage balanced enough to catch language-specific regressions
