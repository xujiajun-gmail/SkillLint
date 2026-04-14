# SkillLint Baselines

This directory stores reproducible baseline snapshots generated from the checked-in example corpora.

## Files

- `examples-balanced-baseline.json`: machine-readable baseline generated from `examples/` and `examples/zh-community/` using the `balanced` profile.

## Regenerate

```bash
python3 scripts/generate_example_baseline.py
```

You can also choose another profile:

```bash
python3 scripts/generate_example_baseline.py --profile strict
```
