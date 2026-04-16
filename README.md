# SkillLint

SkillLint is a security scanner for agent skills.

SkillLint now ships a working CLI baseline with multi-engine scanning, JSON/Markdown/SARIF output, golden-subset evaluation, and an initial corpus of example skills.
It also ships a lightweight web app and REST API for interactive scan workflows.

## Goals

SkillLint is being built as a CLI-first tool that can scan a skill from:
- a local directory
- a zip archive
- a remote URL
- a git repository URL

It is intended to produce:
- machine-readable results for downstream tooling
- a detailed human-readable report
- taxonomy-based security classification
- file or line-level evidence whenever possible

## Current status

### Research & design
- Security research report: `docs/skill-security-threat-research-report.md`
- Formal threat taxonomy: `docs/skilllint-threat-taxonomy.md`
- CLI development plan: `docs/skilllint-cli-development-plan.md`
- Rule catalog: `docs/skilllint-rule-catalog.md`
- Detector architecture: `docs/skilllint-detector-architecture.md`
- Profiles and rule filters: `docs/skilllint-profiles.md`
- Report format: `docs/skilllint-report-format.md`
- SARIF output: `docs/skilllint-sarif-output.md`
- Example baseline snapshot: `docs/skilllint-example-baseline.md`
- Golden labeled subset and evaluation: `docs/skilllint-golden-evaluation.md`
- Correlation scoring: `docs/skilllint-correlation-scoring.md`
- Risk flows / attack-chain metadata: `docs/skilllint-risk-flows.md`
- skill-safe fixture coverage report: `docs/skilllint-skill-safe-coverage-report.md`
- Input validation model: `docs/skilllint-input-validation.md`
- Web deployment notes: `docs/skilllint-web-deployment.md`
- False-positive triage round 1: `docs/skilllint-fp-triage-round1.md`
- False-positive triage round 2: `docs/skilllint-fp-triage-round2.md`
- False-positive triage round 3: `docs/skilllint-fp-triage-round3.md`
- False-positive triage round 4: `docs/skilllint-fp-triage-round4.md`

### Sample collections
- General examples: `examples/`
- Chinese community examples: `examples/zh-community/`

### Implemented in the current baseline
- Python package scaffold
- `skilllint scan <target>` CLI entrypoint
- `skilllint-web` web app + REST API for scan workflows
- `skilllint profiles`
- `skilllint evaluate-golden`
- built-in scan profiles: `balanced`, `strict`, `marketplace-review`, `ci`
- rule filtering by `rule_id` and taxonomy
- target type resolution: directory / zip / URL / git URL
- workspace normalization
- input validation for directory / archive / URL before scanning
- package engine
  - hidden file / archive / binary / symlink / startup artifact checks
  - `package.json` lifecycle scripts
  - remote / VCS dependency detection in `package.json`, `requirements*.txt`, `pyproject.toml`
  - GitHub Actions trigger / permissions / unpinned action checks
  - Dockerfile remote bootstrap checks
  - `skill.json` and `.codex-plugin/plugin.json` permission / endpoint / hook / identity checks
- regex engine
- semantic engine (local heuristics + optional LLM review)
- dataflow engine (Python + shell + JS/TS coverage, opt-in or via profile)
- structured rule catalog under `src/skilllint/rules/`
- taxonomy mapping and finding correlation
- golden labeled subset for regression evaluation
- precision/recall-style rule and taxonomy evaluation
- aggregate correlation scoring in scan summaries
- structured `metadata.risk_flows` for attack-chain / source-to-sink style API and UI consumption
- JSON output
- Markdown report with auto Chinese or English selection
- SARIF 2.1.0 output
- console summary

### Current detector / rule footprint

- Engines: `package`, `regex`, `semantic`, `dataflow`
- Structured rules:
  - regex: 21
  - package: 25
  - semantic: 12
  - dataflow: 8
  - total: 66

### Not implemented yet
- richer LLM semantic workflows (multi-pass triage / consensus / budget policies)
- advanced reputation / cross-skill analysis
- external custom rule packs
- deeper SARIF taxonomy component modeling

## Quick start

```bash
pip install -e .[dev]
skilllint scan ./examples/openai/playwright --output .skilllint-out
```

You can also scan a zip or URL:

```bash
skilllint scan ./skill.zip
skilllint scan https://example.com/skill.zip
skilllint scan https://github.com/openai/skills
```

Run the web app locally:

```bash
pip install -e .[dev]
skilllint-web
```

Then open `http://127.0.0.1:18110`.

You can also configure host and port:

```bash
skilllint-web --host 127.0.0.1 --port 18110
skilllint-web --host 0.0.0.0 --port 18110
skilllint-web --host 0.0.0.0 --port 18110 --workers 2 --log-level info
skilllint-web --reload
```

Or by environment variables:

```bash
export SKILLLINT_WEB_HOST=0.0.0.0
export SKILLLINT_WEB_PORT=18110
export SKILLLINT_WEB_RELOAD=false
export SKILLLINT_WEB_WORKERS=2
export SKILLLINT_WEB_LOG_LEVEL=info
skilllint-web
```

For public/external deployment, bind to `0.0.0.0` and place the service behind your normal firewall/reverse-proxy setup.
For more deployment details, see `docs/skilllint-web-deployment.md`.

The web app supports:
- zip upload
- directory upload
- remote URL scan
- input validation hints and clearer validation-error feedback
- browser-side prechecks for obvious directory/archive/URL validation failures before upload
- bilingual UI with auto/manual zh/en switching
- human-readable report, raw JSON, and Markdown output
- finding-to-source navigation for flagged files

REST API endpoints:

```text
GET  /api/health
POST /api/scan/url
POST /api/scan/archive
POST /api/scan/directory
GET  /api/docs
```

## CLI

```bash
skilllint scan <target> \
  --profile balanced \
  --format both \
  --output .skilllint-out \
  --lang auto
```

Optional deeper analysis:

```bash
skilllint scan <target> --profile strict
skilllint scan <target> --use-dataflow
skilllint scan <target> --use-llm --llm-model gpt-5.4
```

LLM runtime settings can be passed by CLI flags, config file, or environment variables:

```bash
export SKILLLINT_LLM_BASE_URL="https://your-endpoint/v1"
export SKILLLINT_LLM_API_KEY="your-api-key"
export SKILLLINT_LLM_MODEL="your-model"

skilllint scan <target> --use-llm
# or
skilllint scan <target> --use-llm \
  --llm-base-url https://your-endpoint/v1 \
  --llm-api-key your-api-key \
  --llm-model your-model
```

Config files may also include:

```yaml
llm:
  base_url: https://your-endpoint/v1
  api_key: your-api-key
  model: your-model
  debug: false
```

For security, prefer environment variables or CLI secrets over committing API keys.
Use `--llm-debug` only during prompt debugging; it includes raw LLM responses and snippets in scan metadata.

Input validation defaults:

- directory / extracted archive must look like a skill package
- by default, scan input must contain a `SKILL.md` entry
- normalized file count must not exceed `1000`
- archive path traversal / symlink entries are rejected
- path depth / path length are bounded
- single-file and total input size are bounded
- remote URL downloads are size-limited before scan continues
- remote URL scanning rejects unsafe local/private/metadata hosts and embedded URL credentials

Related config keys:

```yaml
inputs:
  max_archive_size_mb: 100
  max_redirects: 5
  max_input_files: 1000
  max_single_file_mb: 20
  max_total_input_mb: 200
  max_path_depth: 20
  max_path_length: 240
  require_skill_entry: true
```

Web/API validation failures return structured error details when the request reaches SkillLint validation:

```json
{
  "detail": {
    "code": "missing_skill_entry",
    "message": "Input is not a skill package: no SKILL.md was found.",
    "metadata": {}
  }
}
```

Profile discovery:

```bash
skilllint profiles
```

Rule and taxonomy filtering:

```bash
skilllint scan <target> --disable-rule PROMPT_INJECTION_PRIORITY
skilllint scan <target> --enable-taxonomy SLT-D01
```

SARIF output:

```bash
skilllint scan <target> --format sarif
skilllint scan <target> --format all
```

Golden subset evaluation:

```bash
skilllint evaluate-golden
skilllint evaluate-golden --profile balanced --output baselines/golden-eval
```

## Repository layout

```text
config/
docs/
examples/
scripts/
src/skilllint/
tests/
```

## Detection engines

SkillLint currently combines four engine families:
- `package`: package structure, symlink, archive, binary, startup artifact, manifest, workflow, Dockerfile risk
- `regex`: high-confidence signatures for prompt injection, exfil, install abuse, persistence, destructive actions
- `semantic`: keyword-group and heuristic semantic analysis, plus optional LLM-assisted review
  - the optional LLM path now emits plain-language semantic labels and maps them locally to SkillLint taxonomy metadata
- `dataflow`: source-to-sink analysis for Python, shell, and JS/TS helpers

Current package/dataflow coverage already includes:

- package / manifest:
  - `SKILL.md` structure checks
  - `skill.json` / `.codex-plugin/plugin.json` risky permissions, startup hooks, local/private/metadata endpoints, floating references, identity mismatch, and underdeclared behavior
  - lifecycle scripts
  - remote dependencies
  - CI workflow risk
  - Dockerfile bootstrap risk
- dataflow:
  - Python secret → network / secret → log / input → exec
  - shell secret → network / input → exec / tainted delete target
  - JS/TS secret → network / input → exec

## Rule catalog

Structured rules now live in:

```text
src/skilllint/rules/
├── regex/rules.yaml
├── package/rules.yaml
├── semantic/rules.yaml
└── dataflow/rules.yaml
```

The scanner exposes rule metadata in findings, and scan metadata includes current catalog counts, active profile, enabled engines, and active rule filters.

## Outputs

SkillLint currently supports:
- JSON
- Markdown
- SARIF 2.1.0

Scan outputs now also include correlation hits, score-breakdown metadata, and `metadata.risk_flows` for explainability.

Example risk-flow IDs include:

- `flow.slt-b01.secret-to-egress`
- `flow.slt-e01.secret-to-log`
- `flow.slt-a03.external-instructions-to-context`
- `flow.slt-b04.instructions-to-persistent-memory`
- `flow.slt-b02.tainted-delete-target`
- `flow.slt-c04.workspace-policy-poisoning`

### JSON summary highlights

Current JSON summaries expose:

- `risk_level`
- `score_risk_level`
- `verdict`
- `base_score`
- `correlation_score`
- `aggregate_score`
- `correlation_count`
- `distinct_files`
- `distinct_taxonomies`

### Finding fields

Current findings include:

- `rule_id`
- `engine`
- `severity`
- `confidence`
- `primary_taxonomy`
- `related_taxonomy`
- `evidence.file`
- `evidence.line_start`
- `evidence.line_end`
- `evidence.snippet`

For full report structure, see:

- `docs/skilllint-report-format.md`

## Baselines

Example corpus baseline artifacts live under `baselines/` and can be regenerated with:

```bash
python3 scripts/generate_example_baseline.py
```

Golden subset evaluation artifacts can be regenerated with:

```bash
python3 scripts/evaluate_golden_subset.py
```

The current shipped golden subset is a larger strict-profile adjudicated set with stronger
coverage for zh-community skills, packaging risks, CI risks, and dataflow cases.

Current evaluation artifacts in-repo reflect a strict-profile golden subset baseline with
precision/recall-style rule and taxonomy metrics.

## License

Apache-2.0
