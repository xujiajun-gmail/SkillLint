# SkillLint v0.2.0 Release Notes

SkillLint v0.2.0 is the first release that adds a dedicated web application and REST API on top of the existing scan engine.

## Highlights

### New web app
This release adds a browser-based SkillLint interface under `src/app/` with:

- zip upload
- local directory upload
- remote URL scan
- bilingual UI with auto/manual zh/en switching
- structured findings view
- Markdown and JSON report views
- source-location-aware code viewer for findings

### New REST API
The web layer is split into UI and service/API so the scan capability can be reused by other tools.

Current API endpoints:

- `GET /api/health`
- `POST /api/scan/url`
- `POST /api/scan/archive`
- `POST /api/scan/directory`
- `GET /api/docs`

### Service/UI decoupling
The new `ScanService` reuses the existing `SkillScanner` pipeline and packages the results into:

- structured `ScanResult` output for integrations
- Markdown report output for human review
- source file payloads for finding-to-code navigation

### Safer web response handling
This release also adds web-specific response hardening:

- temporary workspace paths are sanitized before returning API results
- only finding-related text files are returned to the frontend
- uploaded directory paths are normalized and validated

## Scope

v0.2.0 focuses on scan delivery surfaces rather than adding new detector families.

The current detection baseline remains:

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

- `ruff check src tests`
- `pytest -q`

## Suggested next work

- asynchronous scan jobs and progress reporting
- richer source snippet rendering and diff-style highlighting
- web-side report export flows
- multi-file correlation visualization
- deployment packaging for standalone service hosting
