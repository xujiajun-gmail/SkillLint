# Changelog

All notable changes to this project will be documented in this file.

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
