# SkillLint False-Positive Triage — Round 4 (Semantic / Context Refinement)

- 项目：SkillLint
- 日期：2026-04-14
- 语料：`examples/` + `examples/zh-community/`
- 样本数：200
- Profile：`balanced`
- 目标：继续压低剩余高噪声规则，重点处理“防御性提示”“普通安装/清理说明”“描述型 trigger 文本”与“文档中重复模式刷屏”问题。

---

## 1. Round 3 后剩余的主要问题

Round 3 之后 baseline 已收敛到：

- `total_findings`: **96**
- `malicious`: **6**
- `suspicious`: **40**
- `safe`: **148**

剩余主要噪声集中在：

- `SEMANTIC_HIDDEN_BEHAVIOR`
- `DESTRUCTIVE_FILE_OPERATION`
- `ENV_FILE_CREDENTIAL_REFERENCE`
- `SUSPICIOUS_DOWNLOAD_HOST`
- 少量 `TRIGGER_HIJACK_ANY_TASK`

抽样后发现几个典型问题：

1. **防御性警告被判成 hidden behavior**
   - 例如：
     - “Do NOT use X here because it may silently link the project as a side effect”
   - 这类文本是在提示不要触发隐式副作用，而不是要求对用户隐瞒行为。

2. **clean install / cleanup temp dir 仍被视作 destructive**
   - 如：
     - `rm -rf node_modules pnpm-lock.yaml`
     - `rm -rf "$TEMP_DIR"`
   - 这些更多是工程清理/临时目录清理，不应默认视作高风险破坏行为。

3. **raw.githubusercontent.com 的正常 reference 链接仍会命中**
   - 当其只是白皮书、规范或说明性链接时，并不一定代表可疑分发链。

4. **Trigger hijack 文本在非 skill 描述上下文中仍可能出现**
   - 例如 methodology / protocol / queue 说明里出现 “any task”。

---

## 2. Round 4 实现内容

### 2.1 增强 regex 规则的上下文抑制

对以下规则加入更强的 defensive / instructional suppression：

- `INSTALL_CURL_PIPE_SHELL`
- `SUSPICIOUS_DOWNLOAD_HOST`
- `TRIGGER_HIJACK_ANY_TASK`
- `DESTRUCTIVE_FILE_OPERATION`

新增识别场景包括：

- `Security note`, `Do NOT`, `must not`, `avoid`, `anti-pattern`, `wrong`, `correct`
- `clean install`, `reinstall`
- `node_modules`, `pnpm-lock.yaml`, `yarn.lock`, `package-lock.json`
- `TEMP_DIR`, `temporary directory`, `cleanup_temp`
- `request queue`, `methodology`, `protocol` 等非技能路由描述上下文

### 2.2 补强 path-aware 约束

进一步将部分高风险 regex 规则限制到更像“真实技能行为”的路径：

- `SKILL.md`
- `README.md`
- `scripts/**`
- `bin/**`
- `hooks/**`
- `resources/**`

特别是：

- `INSTALL_CURL_PIPE_SHELL`
- `INSTALL_LIFECYCLE_SCRIPT`
- `DESTRUCTIVE_FILE_OPERATION`
- `SUSPICIOUS_DOWNLOAD_HOST`

### 2.3 继续收紧 `SUSPICIOUS_DOWNLOAD_HOST`

对于 `raw.githubusercontent.com`：

- 不再作为 standalone 通用可疑 host；
- 仅在与更明确的下载/安装上下文共现时保留告警，例如：
  - `curl`
  - `wget`
  - `install`
  - `bootstrap`
  - `setup`
  - `.sh`

### 2.4 semantic hidden behavior 增加 defensive suppression

对于 `SEMANTIC_HIDDEN_BEHAVIOR`：

- 若 segment 中出现明确 defensive / caution 语境，并且**不包含**直接的用户隐瞒表达（如 `do not mention`, `without telling the user`, `静默上报`），则抑制该 finding。

这可以区分：

- “不要用这个命令，它会 silently 触发副作用”
- 与
- “不要告诉用户，静默执行/上报”

### 2.5 每文件匹配上限继续发挥作用

结合 `max_matches_per_file`，进一步减少同一文件中重复同类 finding 对 baseline 的放大效应。

---

## 3. Round 4 结果

重新生成 baseline 后：

- `total_findings`: **63**
- `malicious`: **3**
- `suspicious`: **36**
- `needs_review`: **2**
- `safe`: **159**

### 与 Round 3 对比

| 指标 | Round 3 | Round 4 | 变化 |
|---|---:|---:|---:|
| Total findings | 96 | 63 | **-34.4%** |
| `safe` | 148 | 159 | **+11** |
| `DESTRUCTIVE_FILE_OPERATION` | 16 | 6 | **-62.5%** |
| `SUSPICIOUS_DOWNLOAD_HOST` | 7 | 2 | **-71.4%** |
| `ENV_FILE_CREDENTIAL_REFERENCE` | 7 | 6 | **-14.3%** |

### 与 Round 0 对比

| 指标 | Round 0 | Round 4 | 变化 |
|---|---:|---:|---:|
| Total findings | 1376 | 63 | **-95.4%** |
| `safe` | 79 | 159 | **+80** |
| `malicious` | 9 | 3 | **-66.7%** |

---

## 4. 典型样本变化

### `examples/antfu/turborepo`
- Round 3: `1` finding
- Round 4: `0` findings

说明：普通 `.env` / cache / monorepo 配置说明已经不再被误当成安全问题。

### `examples/apify/apify-ultimate-scraper`
- Round 3: `0` findings
- Round 4: `0` findings

说明：上一轮已经压掉的 `.env` / usage 型噪声继续保持稳定。

### `examples/zh-community/tanweai-pua/pua`
- Round 4: `1` finding
- 仅剩：`SEMANTIC_HIDDEN_BEHAVIOR`

说明：`references/survey.md` 中对危险命令的问卷式描述已不再被误判为 destructive chain，剩余 finding 更接近 skill 本身可疑行为。

### `examples/vercel-labs/vercel-cli-with-tokens`
- Round 4: 仍有 `ENV_FILE_CREDENTIAL_REFERENCE` + `SEMANTIC_HIDDEN_BEHAVIOR`

说明：这类 skill 仍包含值得人工审查的“token from .env”与“silent side effect”相关语义，但误报规模已明显可控。

---

## 5. 当前剩余的主要规则

Round 4 后 top rules 为：

- `SEMANTIC_HIDDEN_BEHAVIOR`: 14
- `SEMANTIC_PERMISSION_DRIFT`: 10
- `PROMPT_INJECTION_PRIORITY`: 7
- `DESTRUCTIVE_FILE_OPERATION`: 6
- `ENV_FILE_CREDENTIAL_REFERENCE`: 6
- `INSTALL_CURL_PIPE_SHELL`: 3
- `DANGEROUS_SHELL_EXEC`: 3

这表明当前误报治理已经进入最后一段更细粒度阶段，剩余重点不再是“大面积规则过宽”，而是：

1. **Skill 描述中的真实风险与正常操作边界**
2. **语义规则对 warning / anti-pattern / side-effect 描述的进一步区分**
3. **对 medium-risk 凭证处理说明是否继续降噪或分级**

---

## 6. 本轮结论

Round 4 证明：

- 通过 `path-aware + context-aware + per-file cap + rule split` 的组合，SkillLint 的 baseline 已从最初的 **1376 findings** 压到 **63 findings**；
- `safe` 样本数从 **79** 提升到 **159**；
- 现阶段剩余 finding 已显著更接近“值得人工审查”的集合，而不是大规模静态噪声。

下一步更适合做的事情已经不是继续大刀阔斧降噪，而是：

- 建立 **golden labeled subset**；
- 对剩余高价值规则做精细 precision / recall 调优；
- 引入 correlation/scoring，把多个弱信号组合成更稳定的裁决。
