# SkillLint v0.1.1 Release Notes

SkillLint v0.1.1 is the first post-`v0.1.0` baseline refinement release. It does not change the product direction, but substantially improves detector coverage, LLM ergonomics, golden evaluation, and report/readme quality.

## Highlights

### Golden evaluation and scoring baseline
This release adds and stabilizes:

- a golden labeled subset
- `skilllint evaluate-golden`
- precision/recall-style rule and taxonomy evaluation
- correlation scoring and score-breakdown metadata

### Better LLM-assisted semantic review
LLM integration is now more practical:

- dedicated runtime env vars:
  - `SKILLLINT_LLM_BASE_URL`
  - `SKILLLINT_LLM_API_KEY`
  - `SKILLLINT_LLM_MODEL`
- matching CLI flags
- config-file support
- plain-language semantic labels mapped locally to SkillLint taxonomy/rule metadata
- deduplication for repeated LLM findings
- opt-in `--llm-debug`

### Deeper package and automation scanning
`package` analysis now covers:

- `package.json` lifecycle scripts
- remote / VCS dependencies
- `requirements*.txt` / `pyproject.toml` remote dependencies
- GitHub Actions:
  - dangerous triggers
  - elevated permissions
  - unpinned actions
- Dockerfile remote bootstrap patterns

### Deeper dataflow coverage
`dataflow` analysis now covers:

- expanded Python source/sink coverage
- async Python execution sinks
- shell heuristics
- JS/TS secret → network
- JS/TS input → exec

### Better Markdown reports and docs
Human-readable reporting is improved with:

- overview tables
- taxonomy / severity tables
- top findings section
- structured per-finding detail tables
- refreshed README / development plan / rule catalog
- detector architecture and report format docs

## Included commands

- `skilllint scan`
- `skilllint profiles`
- `skilllint evaluate-golden`

## Current baseline snapshot

- Engines:
  - `package`
  - `regex`
  - `semantic`
  - `dataflow`
- Structured rules:
  - regex: 18
  - package: 15
  - semantic: 11
  - dataflow: 6
  - total: 50

## Known limitations

- LLM workflow is still enhancement-only, not a full multi-pass adjudication system.
- Cross-skill / reputation analysis is not implemented.
- External custom rule packs are not implemented.
- SARIF taxonomy modeling is still basic.
- `fail-on` severity gating is not implemented yet.

## Suggested next work

- larger real-world regression baselines
- richer LLM triage / consensus workflows
- external rule pack / plugin model
- deeper SARIF taxonomy integration
- cross-skill / reputation analysis
