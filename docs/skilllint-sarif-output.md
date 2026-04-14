# SkillLint SARIF Output

- 项目：SkillLint
- 日期：2026-04-14
- 状态：Implemented Baseline

## 1. 目标

SkillLint 已支持输出 **SARIF 2.1.0**，方便接入：

- GitHub code scanning
- CI 安全流水线
- 安全平台聚合
- 下游规则统计与审计系统

---

## 2. CLI 用法

### 仅输出 SARIF

```bash
skilllint scan ./skill --format sarif
```

默认写入：

```text
.skilllint-out/result.sarif.json
```

### 同时输出 JSON / Markdown / SARIF

```bash
skilllint scan ./skill --format all
```

---

## 3. 当前格式支持

| `--format` | 输出 |
|---|---|
| `json` | `result.json` |
| `markdown` | `report.md` |
| `both` | `result.json` + `report.md` |
| `sarif` | `result.sarif.json` |
| `all` | `result.json` + `report.md` + `result.sarif.json` |

---

## 4. SkillLint -> SARIF 映射

### rule 映射

SkillLint 的 `rule_id` 会映射到 SARIF 的：

- `tool.driver.rules[].id`
- `results[].ruleId`

并保留：

- title
- explanation
- remediation
- severity
- confidence
- taxonomy
- engine
- tags

### severity 映射

| SkillLint | SARIF level |
|---|---|
| `critical` | `error` |
| `high` | `error` |
| `medium` | `warning` |
| `low` | `note` |
| `info` | `note` |

### confidence 映射

| SkillLint | SARIF precision |
|---|---|
| `high` | `very-high` |
| `medium` | `high` |
| `low` | `medium` |

### location 映射

若 finding 带有源文件定位信息，则会映射到：

- `results[].locations[].physicalLocation.artifactLocation.uri`
- `region.startLine`
- `region.endLine`
- `region.snippet.text`

---

## 5. 附加属性

SkillLint 还会在 SARIF 的 `properties` 中保留一些上下文信息，例如：

- `profile`
- `enabled_engines`
- `rule_filters`
- `summary`
- `taxonomy`
- `related_taxonomy`
- `skilllint_finding_id`

这有助于后续在平台侧做聚类、回归和误报分析。

---

## 6. 当前限制

当前 SARIF 输出是 v0.1 基线能力，已可用于 CI 集成，但仍有一些后续可增强点：

1. 更严格的原始源码路径恢复（尤其是 zip / url / git 输入）；
2. 更丰富的 `helpUri` / taxonomy descriptors；
3. GitHub code scanning 专项字段优化；
4. 自动把 SkillLint taxonomy 正式映射成 SARIF taxonomy component。
