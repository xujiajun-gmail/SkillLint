# SkillLint v0.2.1 Release Notes

SkillLint v0.2.1 is a focused web UX and frontend behavior fix release for the new SkillLint web app introduced in v0.2.0.

## Highlights

### Fixed input pane switching
The scan setup area now correctly shows only the active input mode:

- zip upload
- directory upload
- URL input

This fixes the previous issue where multiple input panes could appear at the same time.

### Fixed directory upload scan flow
This release fixes the directory-upload path in the web app so browser-selected local directories can be submitted reliably to the backend scan API.

### Improved source viewer behavior
The source viewer is now more usable for larger files:

- source content is displayed inside a scrollable panel
- clicking a finding scrolls the relevant code location into view
- the target line is positioned closer to the center of the viewport
- highlighted lines are easier to identify

### Better handling for findings without source files
When a finding does not have a file-level source location, or when the original file is unavailable in the current API response, the right-side panel now renders a useful fallback detail view instead of only showing an empty prompt.

## Scope

v0.2.1 does not change the underlying detector families or scoring model.

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

- add browser-based integration tests for the web app
- improve source-view context folding
- support exportable HTML/PDF reports
- add async scan progress and job history
