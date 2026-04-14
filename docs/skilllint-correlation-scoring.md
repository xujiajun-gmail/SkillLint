# SkillLint Correlation Scoring

SkillLint now uses a two-layer decision model:

1. **Rule findings** from package / regex / semantic / dataflow engines
2. **Aggregate scoring + correlation hits** to summarize risk and set verdicts more realistically

## Why

A plain `max(severity)` policy was too coarse:

- a single `critical` install pattern could incorrectly look "malicious"
- multiple medium/high signals in the same file were under-modeled
- rule-level hits lacked a systematic way to express compounding risk

## Summary Fields

`ScanSummary` now includes:

- `risk_level`
- `score_risk_level`
- `verdict`
- `base_score`
- `correlation_score`
- `aggregate_score`
- `correlation_count`
- `distinct_files`
- `distinct_taxonomies`

Scan metadata also includes:

- `correlation_hits`
- `score_breakdown.finding_contributions`
- `score_breakdown.correlation_contributions`
- `score_breakdown.top_*` summaries

## Score Construction

### Base score

Each non-correlation finding contributes weighted points based on:

- severity
- confidence
- engine type
- diminishing returns for repeated hits of the same rule

### Correlation score

Additional boosts are added for:

- known high-risk rule chains
- same-file dense signal concentration
- multi-engine confirmation
- multi-taxonomy overlap
- repository-wide multiple high-risk findings

## High-signal correlation patterns

Current explicit patterns include examples such as:

- secret-path + external send
- env-credential + external send
- semantic exfil + external send
- prompt-priority override + external send
- remote install bootstrap chains
- destructive-exec chains
- credential automation + hidden behavior

Some patterns also emit synthetic correlation findings such as:

- `CORRELATED_SECRET_EXFIL_CHAIN`
- `CORRELATED_PRIORITY_EXFIL`

These make the chain visible in JSON / Markdown / SARIF outputs.

## Verdict Semantics

The scanner now separates **risk** from **verdict** more clearly:

- `risk_level` reflects worst-case technical severity after scoring
- `verdict` is stricter and reserves `malicious` for high-confidence exfil / reverse-shell / correlation-chain style cases

This keeps high-risk-but-legitimate operational skills in `suspicious` rather than overcalling them as `malicious`.

## Where It Appears

- console summary
- JSON output
- Markdown report
- SARIF run properties
