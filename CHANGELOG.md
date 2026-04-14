# Changelog

All notable changes to this project will be documented in this file.

## [Unreleased]

### Added
- Golden labeled subset under `golden/skilllint-golden-subset.yaml`.
- Synthetic evaluation fixtures under `golden/fixtures/`.
- Golden evaluation module and `scripts/evaluate_golden_subset.py`.
- `skilllint evaluate-golden` CLI command.
- Documentation for golden evaluation and correlation scoring.

### Improved
- Aggregate correlation scoring in scan summaries.
- Score breakdown metadata for top finding and correlation contributors.
- Verdict semantics so high-risk operational skills are less likely to be overcalled as malicious.
- Additional suppression/tuning for semantic exfiltration, permission drift, and prompt-priority false positives.
- Expanded the shipped golden subset to 70+ adjudicated samples with better zh, package, CI, and dataflow coverage.
- Refactored the optional LLM analyzer to return plain-language semantic labels that are mapped locally to SkillLint rule/taxonomy metadata.
- Added dedicated LLM runtime settings through `SKILLLINT_LLM_BASE_URL`, `SKILLLINT_LLM_API_KEY`, `SKILLLINT_LLM_MODEL`, config-file fields, and matching `scan` CLI flags.
- Added LLM finding deduplication plus opt-in `--llm-debug` raw response capture for prompt debugging.

## [0.1.0] - 2026-04-14

### Added
- Initial `skilllint` CLI with `scan` and `profiles` commands.
- Multi-input support for local directories, zip archives, remote URLs, and Git repository URLs.
- Multi-engine scanning pipeline:
  - package analysis
  - regex analysis
  - semantic analysis
  - dataflow analysis
- Optional LLM-assisted semantic review.
- Structured rule catalog under `src/skilllint/rules/`.
- Built-in scan profiles: `balanced`, `strict`, `marketplace-review`, `ci`.
- Rule filtering by `rule_id` and taxonomy.
- Output renderers for:
  - JSON
  - Markdown
  - SARIF 2.1.0
  - console summary
- Threat taxonomy and rule catalog documentation.
- Example corpus collection:
  - 100 general skills
  - 100 Chinese community skills
- Baseline generation pipeline and reproducible example baseline artifacts.
- False-positive triage documentation for rounds 1 through 4.

### Improved
- Iterative false-positive reduction using baseline-driven tuning.
- Path-aware and context-aware rule suppression.
- Per-file rule match limiting for noisy repeated patterns.
- Split handling for high-risk secret path references vs lower-risk `.env` credential references.

### Validation
- Unit test suite expanded to cover:
  - scanner smoke tests
  - semantic engine behavior
  - dataflow engine behavior
  - profile and rule filter behavior
  - SARIF rendering
  - baseline generation
  - rule tuning and path-aware filtering
