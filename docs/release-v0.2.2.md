# SkillLint v0.2.2 Release Notes

SkillLint v0.2.2 is a detector coverage and structured-risk-output release. It focuses on closing gaps found by comparing SkillLint against the `skill-safe` fixture set and on making scan results easier for tools and UI layers to consume as attack chains.

## Highlights

### Broader skill manifest and plugin manifest coverage

The package engine now parses and analyzes:

- `skill.json`
- `.codex-plugin/plugin.json`

New manifest-level checks cover:

- risky permissions such as shell, network, and filesystem write capabilities
- startup / bootstrap hooks
- localhost, private-network, and cloud metadata endpoints
- floating repository or update references
- manifest identity vs `SKILL.md` title mismatch
- manifest capability vs documentation alignment issues
- hidden unicode / zero-width markers in key skill files

Manifest findings now include better source evidence where possible, including file and line location.

### Better coverage for skill-safe style risk fixtures

This release adds or improves detection for:

- credential leakage to stdout/logs
- destructive shell delete targets controlled by variables
- hidden-behavior suppression edge cases such as `Do not tell the user`
- trusted tool-output / external-instruction propagation
- `MEMORY.md` persistence
- `.env` and `.cursor/rules.mdc` workspace poisoning
- floating supply-chain references
- hidden unicode markers
- trust / identity mismatch between manifest and documentation

The new coverage report is documented in:

- `docs/skilllint-skill-safe-coverage-report.md`

### New structured risk-flow metadata

Scan JSON metadata now includes `metadata.risk_flows`, a deterministic attack-chain view derived from findings.

Current flow IDs include:

- `flow.slt-b01.secret-to-egress`
- `flow.slt-e01.secret-to-log`
- `flow.slt-a03.external-instructions-to-context`
- `flow.slt-b04.instructions-to-persistent-memory`
- `flow.slt-b02.tainted-delete-target`
- `flow.slt-c04.workspace-policy-poisoning`

Each flow includes:

- flow id and title
- primary taxonomy
- severity
- file when known
- triggered rule IDs
- `evidence_refs` pointing back to original finding IDs
- path labels suitable for UI rendering

Design details:

- `docs/skilllint-risk-flows.md`

### Rule catalog expansion

The structured rule catalog now contains:

- regex: 21
- package: 25
- semantic: 12
- dataflow: 8
- total: 66

## Scope

v0.2.2 does not add a new command or a new detector family. It strengthens the existing scanner by:

- expanding package / manifest understanding
- improving semantic and regex risk coverage
- adding two dataflow rules
- adding structured flow metadata for downstream API/UI consumers

## Validation

- `ruff check src tests`
- `pytest -q`

Current validation result at release time:

- 75 tests passed

## Suggested next work

- expose risk flows more prominently in the web UI report
- add a dedicated `diff` command for taxonomy/finding/flow drift
- add policy gating such as `fail-on` and fine-grained allow/deny toggles
- enrich `risk_flows` with explicit source/sink nodes
- add browser-level tests for the web app
