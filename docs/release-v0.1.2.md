# SkillLint v0.1.2 Release Notes

SkillLint v0.1.2 is a readability and maintainability release. It does not introduce new detection behavior; instead, it makes the current baseline easier for humans to understand, maintain, and extend.

## Highlights

### Core code is now easier to read
This release adds necessary Chinese comments to the main execution path, including:

- CLI and config loading
- target resolution and workspace preparation
- scanner orchestration
- rule repository and taxonomy mapping
- package / semantic / LLM / dataflow engines
- correlation scoring
- Markdown reporting

The goal is to help human contributors understand:

- module responsibilities
- data flow between layers
- why specific design choices were made
- where future extensions should be added

### New system design document
This release adds:

- `docs/skilllint-system-design-and-implementation.md`

The document explains:

- SkillLint CLI design goals and principles
- system architecture and processing flow
- major module responsibilities
- design and implementation logic
- tradeoffs versus alternative approaches

## Scope

v0.1.2 is intentionally a non-functional release:

- no new detector families
- no new rule categories
- no new output formats
- no scoring changes

Instead, it improves developer onboarding and long-term maintainability.

## Current baseline remains

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

## Validation

- `ruff check` passed
- full test suite passed

## Suggested next work

- larger real-world regression baselines
- richer LLM semantic workflows
- external custom rule packs
- deeper SARIF taxonomy integration
- cross-skill / reputation analysis
