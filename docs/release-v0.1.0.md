# SkillLint v0.1.0 Release Notes

SkillLint v0.1.0 is the first usable CLI-first release of the project.

## Highlights

### CLI-first skill security scanner
You can now scan agent skills from:
- local directories
- zip archives
- remote URLs
- Git repository URLs

Example:

```bash
skilllint scan ./skill --format both
skilllint scan ./skill.zip --format sarif
skilllint scan https://github.com/openai/skills --profile strict
```

### Multi-engine analysis
v0.1.0 includes four analysis families:
- package
- regex
- semantic
- dataflow

### Multiple output formats
Supported outputs:
- JSON
- Markdown
- SARIF 2.1.0
- console summary

### Threat taxonomy and rule catalog
This release establishes the initial SkillLint threat taxonomy and structured rule catalog, providing stable:
- taxonomy codes
- rule IDs
- severity/confidence metadata
- reporting fields for downstream tooling

### Example corpus and baseline workflow
The repository now includes:
- 100 general skill samples
- 100 Chinese community skill samples
- reproducible baseline generation
- baseline tuning and false-positive triage documents

## What is included
- `skilllint scan <target>`
- `skilllint profiles`
- built-in profiles:
  - `balanced`
  - `strict`
  - `marketplace-review`
  - `ci`
- rule filters:
  - `--enable-rule`
  - `--disable-rule`
  - `--enable-taxonomy`
  - `--disable-taxonomy`
- optional:
  - `--use-dataflow`
  - `--use-llm`

## Baseline status
Current checked-in balanced baseline on the 200-sample corpus:
- total findings: **63**
- safe samples: **159**
- suspicious samples: **36**
- malicious samples: **3**

## Known limitations
- LLM workflow is still minimal and enhancement-only.
- Baseline results are regression snapshots, not ground-truth labels.
- Source path restoration for some zip/url/git cases can still improve.
- SARIF taxonomy modeling is still basic.
- External custom rule packs are not yet implemented.

## Next likely work
- golden labeled subset / adjudication framework
- precision/recall style evaluation for remaining rules
- richer correlation/scoring
- external custom rules
