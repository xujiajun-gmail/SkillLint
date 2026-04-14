# SkillLint Example Baseline

- Generated at: `2026-04-14T06:00:35.762936+00:00`
- Profile: `balanced`
- Tool version: `0.1.0`
- Sample count: `200`
- Failure count: `0`
- Total findings: `63`

> Note: this baseline is a reproducibility dataset and regression snapshot, not a ground-truth maliciousness label set.
> High counts on popular public skills usually indicate rule sensitivity and false-positive tuning opportunities, not confirmed compromise.

## How to Regenerate

```bash
python3 scripts/generate_example_baseline.py
```

## Verdict Distribution

- `malicious`: 3
- `needs_review`: 2
- `safe`: 159
- `suspicious`: 36

## Risk Distribution

- `critical`: 3
- `high`: 36
- `info`: 159
- `medium`: 2

## Top Taxonomies

- `SLT-A02`: 14
- `SLT-E03`: 10
- `SLT-A01`: 7
- `SLT-B02`: 6
- `SLT-E01`: 6
- `SLT-C04`: 5
- `SLT-B04`: 3
- `SLT-E02`: 3
- `SLT-B01`: 3
- `SLT-C01`: 3
- `SLT-A05`: 2
- `SLT-B05`: 1

## Top Rules

- `SEMANTIC_HIDDEN_BEHAVIOR`: 14
- `SEMANTIC_PERMISSION_DRIFT`: 10
- `PROMPT_INJECTION_PRIORITY`: 7
- `DESTRUCTIVE_FILE_OPERATION`: 6
- `ENV_FILE_CREDENTIAL_REFERENCE`: 6
- `SEMANTIC_MEMORY_PERSISTENCE`: 3
- `DANGEROUS_SHELL_EXEC`: 3
- `INSTALL_CURL_PIPE_SHELL`: 3
- `SEMANTIC_EXFIL_MASQUERADE`: 2
- `SUSPICIOUS_DOWNLOAD_HOST`: 2
- `SEMANTIC_TOOL_POISONING`: 1
- `SYSTEM_PROFILE_MODIFICATION`: 1
- `TRIGGER_HIJACK_ANY_TASK`: 1
- `SEMANTIC_TRIGGER_HIJACK`: 1
- `PACKAGE_ARCHIVE_EMBEDDED`: 1

## By Community

### general

- samples: 100
- findings: 38
- risk:critical: 2
- risk:high: 23
- risk:info: 75
- verdict:malicious: 2
- verdict:safe: 75
- verdict:suspicious: 23

### zh

- samples: 100
- findings: 25
- risk:critical: 1
- risk:high: 13
- risk:info: 84
- risk:medium: 2
- verdict:malicious: 1
- verdict:needs_review: 2
- verdict:safe: 84
- verdict:suspicious: 13

## By Source

### antfu

- samples: 17
- findings: 2
- risk:high: 2
- risk:info: 15
- verdict:safe: 15
- verdict:suspicious: 2

### apify

- samples: 4
- findings: 1
- risk:high: 1
- risk:info: 3
- verdict:safe: 3
- verdict:suspicious: 1

### callstack

- samples: 5
- findings: 0
- risk:info: 5
- verdict:safe: 5

### everything-claude-code-zh

- samples: 58
- findings: 14
- risk:critical: 1
- risk:high: 8
- risk:info: 49
- verdict:malicious: 1
- verdict:safe: 49
- verdict:suspicious: 8

### khazix-skills

- samples: 2
- findings: 0
- risk:info: 2
- verdict:safe: 2

### obsidian

- samples: 5
- findings: 1
- risk:high: 1
- risk:info: 4
- verdict:safe: 4
- verdict:suspicious: 1

### openai

- samples: 43
- findings: 18
- risk:critical: 2
- risk:high: 9
- risk:info: 32
- verdict:malicious: 2
- verdict:safe: 32
- verdict:suspicious: 9

### openai-system

- samples: 2
- findings: 2
- risk:high: 2
- verdict:suspicious: 2

### partme-full-stack-skills

- samples: 14
- findings: 0
- risk:info: 14
- verdict:safe: 14

### shareai-skills

- samples: 4
- findings: 4
- risk:high: 2
- risk:info: 2
- verdict:safe: 2
- verdict:suspicious: 2

### skillcreatorai

- samples: 17
- findings: 5
- risk:high: 3
- risk:info: 14
- verdict:safe: 14
- verdict:suspicious: 3

### tanweai-pua

- samples: 11
- findings: 5
- risk:high: 3
- risk:info: 7
- risk:medium: 1
- verdict:needs_review: 1
- verdict:safe: 7
- verdict:suspicious: 3

### vercel-labs

- samples: 7
- findings: 9
- risk:high: 5
- risk:info: 2
- verdict:safe: 2
- verdict:suspicious: 5

### xstongxue-best-skills

- samples: 11
- findings: 2
- risk:info: 10
- risk:medium: 1
- verdict:needs_review: 1
- verdict:safe: 10

## Top Risky Samples

### examples/zh-community/everything-claude-code-zh/autonomous-loops

- source: `everything-claude-code-zh`
- community: `zh`
- risk: `critical`
- verdict: `malicious`
- findings: `3`
- top_taxonomies: `SLT-C01, SLT-E03, SLT-C04`
- top_rules: `INSTALL_CURL_PIPE_SHELL, SEMANTIC_PERMISSION_DRIFT, SUSPICIOUS_DOWNLOAD_HOST`

### examples/openai/sentry

- source: `openai`
- community: `general`
- risk: `critical`
- verdict: `malicious`
- findings: `2`
- top_taxonomies: `SLT-C01, SLT-E03`
- top_rules: `INSTALL_CURL_PIPE_SHELL, SEMANTIC_PERMISSION_DRIFT`

### examples/openai/render-deploy

- source: `openai`
- community: `general`
- risk: `critical`
- verdict: `malicious`
- findings: `2`
- top_taxonomies: `SLT-C01, SLT-C04`
- top_rules: `INSTALL_CURL_PIPE_SHELL, SUSPICIOUS_DOWNLOAD_HOST`

### examples/vercel-labs/vercel-cli-with-tokens

- source: `vercel-labs`
- community: `general`
- risk: `high`
- verdict: `suspicious`
- findings: `4`
- top_taxonomies: `SLT-E01, SLT-A02`
- top_rules: `ENV_FILE_CREDENTIAL_REFERENCE, SEMANTIC_HIDDEN_BEHAVIOR`

### examples/zh-community/shareai-skills/agent-builder

- source: `shareai-skills`
- community: `zh`
- risk: `high`
- verdict: `suspicious`
- findings: `3`
- top_taxonomies: `SLT-E02, SLT-B02`
- top_rules: `DANGEROUS_SHELL_EXEC, DESTRUCTIVE_FILE_OPERATION`

### examples/skillcreatorai/best-practices

- source: `skillcreatorai`
- community: `general`
- risk: `high`
- verdict: `suspicious`
- findings: `3`
- top_taxonomies: `SLT-A01, SLT-B04`
- top_rules: `PROMPT_INJECTION_PRIORITY, SEMANTIC_MEMORY_PERSISTENCE`

### examples/openai/cloudflare-deploy

- source: `openai`
- community: `general`
- risk: `high`
- verdict: `suspicious`
- findings: `3`
- top_taxonomies: `SLT-A05, SLT-C04`
- top_rules: `SYSTEM_PROFILE_MODIFICATION, TRIGGER_HIJACK_ANY_TASK, SEMANTIC_TRIGGER_HIJACK`

### examples/zh-community/tanweai-pua/shot

- source: `tanweai-pua`
- community: `zh`
- risk: `high`
- verdict: `suspicious`
- findings: `2`
- top_taxonomies: `SLT-E03, SLT-A02`
- top_rules: `SEMANTIC_PERMISSION_DRIFT, SEMANTIC_HIDDEN_BEHAVIOR`

### examples/zh-community/everything-claude-code-zh/skill-stocktake

- source: `everything-claude-code-zh`
- community: `zh`
- risk: `high`
- verdict: `suspicious`
- findings: `2`
- top_taxonomies: `SLT-B02`
- top_rules: `DESTRUCTIVE_FILE_OPERATION`

### examples/zh-community/everything-claude-code-zh/docker-patterns

- source: `everything-claude-code-zh`
- community: `zh`
- risk: `high`
- verdict: `suspicious`
- findings: `2`
- top_taxonomies: `SLT-E03, SLT-E01`
- top_rules: `SEMANTIC_PERMISSION_DRIFT, ENV_FILE_CREDENTIAL_REFERENCE`

### examples/zh-community/everything-claude-code-zh/configure-ecc

- source: `everything-claude-code-zh`
- community: `zh`
- risk: `high`
- verdict: `suspicious`
- findings: `2`
- top_taxonomies: `SLT-B02`
- top_rules: `DESTRUCTIVE_FILE_OPERATION`

### examples/vercel-labs/deploy-to-vercel

- source: `vercel-labs`
- community: `general`
- risk: `high`
- verdict: `suspicious`
- findings: `2`
- top_taxonomies: `SLT-A02, SLT-C04`
- top_rules: `SEMANTIC_HIDDEN_BEHAVIOR, PACKAGE_ARCHIVE_EMBEDDED`

### examples/openai/figma-use

- source: `openai`
- community: `general`
- risk: `high`
- verdict: `suspicious`
- findings: `2`
- top_taxonomies: `SLT-E03, SLT-A01`
- top_rules: `SEMANTIC_PERMISSION_DRIFT, PROMPT_INJECTION_PRIORITY`

### examples/openai/cli-creator

- source: `openai`
- community: `general`
- risk: `high`
- verdict: `suspicious`
- findings: `2`
- top_taxonomies: `SLT-E03, SLT-B01`
- top_rules: `SEMANTIC_PERMISSION_DRIFT, SEMANTIC_EXFIL_MASQUERADE`

### examples/openai/chatgpt-apps

- source: `openai`
- community: `general`
- risk: `high`
- verdict: `suspicious`
- findings: `2`
- top_taxonomies: `SLT-B05, SLT-E03`
- top_rules: `SEMANTIC_TOOL_POISONING, SEMANTIC_PERMISSION_DRIFT`

### examples/zh-community/tanweai-pua/pua

- source: `tanweai-pua`
- community: `zh`
- risk: `high`
- verdict: `suspicious`
- findings: `1`
- top_taxonomies: `SLT-A02`
- top_rules: `SEMANTIC_HIDDEN_BEHAVIOR`

### examples/zh-community/tanweai-pua/pro

- source: `tanweai-pua`
- community: `zh`
- risk: `high`
- verdict: `suspicious`
- findings: `1`
- top_taxonomies: `SLT-A02`
- top_rules: `SEMANTIC_HIDDEN_BEHAVIOR`

### examples/zh-community/shareai-skills/vibe-coding

- source: `shareai-skills`
- community: `zh`
- risk: `high`
- verdict: `suspicious`
- findings: `1`
- top_taxonomies: `SLT-A02`
- top_rules: `SEMANTIC_HIDDEN_BEHAVIOR`

### examples/zh-community/everything-claude-code-zh/security-scan

- source: `everything-claude-code-zh`
- community: `zh`
- risk: `high`
- verdict: `suspicious`
- findings: `1`
- top_taxonomies: `SLT-A02`
- top_rules: `SEMANTIC_HIDDEN_BEHAVIOR`

### examples/zh-community/everything-claude-code-zh/security-review

- source: `everything-claude-code-zh`
- community: `zh`
- risk: `high`
- verdict: `suspicious`
- findings: `1`
- top_taxonomies: `SLT-B01`
- top_rules: `SECRET_PATH_ACCESS`
