# SkillLint False-Positive Triage — Round 1

- 项目：SkillLint
- 日期：2026-04-14
- 语料：`examples/` + `examples/zh-community/`
- 样本数：200
- Profile：`balanced`
- 目的：基于 baseline 做第一轮高噪声规则治理，降低明显误报，同时尽量保留高价值检测覆盖。

---

## 1. Round 0 问题概览

初始 baseline（同一语料、同一 profile）表现出明显的高噪声问题：

- `total_findings`: **1376**
- `malicious`: **9**
- `suspicious`: **112**
- `safe`: **79**

最显著的问题是 `SLT-B01` 相关规则过于敏感：

- `SLT-B01`: **1113**
- `SEMANTIC_EXFIL_MASQUERADE`: **508**
- `SECRET_PATH_ACCESS`: **428**
- `NETWORK_EXFIL_SEND`: **156**
- `DANGEROUS_SHELL_EXEC`: **91**

### 主要误报模式

通过抽样查看 `examples/openai/cloudflare-deploy`、`examples/openai/security-best-practices`、`examples/zh-community/partme-full-stack-skills/build-skills__rspack` 等高噪声样本，发现主要误报来源为：

1. **URL 被当成“外传”信号**
   - 仅因为文档里存在 `https://...` 就触发了外传语义判断；
   - 导致大量普通参考文档、官方链接被误判为 `SEMANTIC_EXFIL_MASQUERADE`。

2. **`.env` 模式过宽**
   - `SECRET_PATH_ACCESS` 中的 `\.env\b` 会误伤诸如 `this.env`、`process.env`、配置字段名等普通用法；
   - 在 SDK/reference 文档中尤为严重。

3. **泛化 `exec(` 匹配过宽**
   - `DANGEROUS_SHELL_EXEC` 会误伤如 `sql.exec(...)`、普通对象方法 `.exec(...)`；
   - 安全文档中“示例漏洞代码”也会被大量命中。

4. **整文件级语义匹配过粗**
   - 只要一个文件同时出现“support/audit”与“upload/https”等词，就会命中；
   - 对大型 reference skill 和示例库尤其不友好。

5. **许可证文本参与语义扫描**
   - `LICENSE.txt` 中的 `support` / `liability` 等词会触发语义规则；
   - 这类文本几乎不应参与安全语义判断。

---

## 2. Round 1 调优内容

本轮已落地以下调优：

### 2.1 `SEMANTIC_EXFIL_MASQUERADE`

从“文件级宽匹配”改为更严格的语义组合：

- 不再把单纯的 `http://` / `https://` 视为 `send` 信号；
- 新增 `data_targets` 关键词组；
- 现在必须同时满足：
  - `masking`
  - `send`
  - `data_targets`
- 并且要求这些信号出现在**同一文本 segment（段落）**中。

效果：大量“支持文档 + 官方链接”误报被消除。

### 2.2 `NETWORK_EXFIL_SEND`

把 regex 从“泛 POST/PUT/URL”收紧为更偏攻击链语义的模式：

- 强调 `upload/send/export/forward` + `conversation/history/token/secret/document/...` + URL；
- 对代码发送行为，要求伴随 `authorization/api_key/token/secret/.env/...` 等敏感上下文。

### 2.3 `SECRET_PATH_ACCESS`

收紧敏感文件匹配：

- 不再把任意 `.env` 子串当作敏感文件；
- 改为更像真实路径/文件名的上下文匹配；
- 避免误伤 `this.env` / 普通对象属性。

### 2.4 `DANGEROUS_SHELL_EXEC`

收紧危险执行原语匹配：

- 不再把任意 `.exec(` 当作危险执行；
- 保留：
  - `os.system(`
  - `subprocess(... shell=True)`
  - `child_process.exec/execSync`
  - 顶层 `eval(` / `exec(`

### 2.5 License 文件跳过

`regex` 与 `semantic` 引擎现在会跳过：

- `LICENSE`
- `LICENSE.txt`
- `COPYING`
- `NOTICE`

---

## 3. Round 1 结果

调优后重新生成 baseline：

- `total_findings`: **429**
- `malicious`: **7**
- `suspicious`: **55**
- `needs_review`: **4**
- `safe`: **134**

### 关键指标变化

| 指标 | Round 0 | Round 1 | 变化 |
|---|---:|---:|---:|
| Total findings | 1376 | 429 | **-68.8%** |
| `SLT-B01` | 1113 | 231 | **-79.2%** |
| `SEMANTIC_EXFIL_MASQUERADE` | 508 | 14 | **-97.2%** |
| `NETWORK_EXFIL_SEND` | 156 | 11 | **-92.9%** |
| `DANGEROUS_SHELL_EXEC` | 91 | 27 | **-70.3%** |
| `SECRET_PATH_ACCESS` | 428 | 204 | **-52.3%** |

### 结果解读

这说明第一轮调优已显著压低“URL/文档/参考资料”带来的大面积误报，尤其是：

- 语义型外传误报基本被压缩到了可管理水平；
- 泛化网络发送规则明显收敛；
- 泛化 `.exec(` 误判显著下降；
- 但 `SECRET_PATH_ACCESS` 仍然偏吵，仍是下一轮重点对象。

---

## 4. Round 1 后仍然明显偏吵的规则

### 4.1 `SECRET_PATH_ACCESS`
当前仍有 **204** 次命中，是最主要的剩余噪声来源。

主要剩余误报模式：

- 技术文档中正当讨论 `.env`、secret manager、凭证治理；
- skill 自身的缓存/环境变量配置说明；
- 安全规范文档中“不要提交 `.env`”之类的防御性说明。

代表样本：

- `examples/antfu/turborepo`
- `examples/openai/security-best-practices`
- `examples/apify/apify-ultimate-scraper`

### 4.2 `DANGEROUS_SHELL_EXEC`
当前剩余 **27** 次命中。

主要剩余模式：

- 安全规范文档中展示危险代码反例（例如 `exec(req.query.cmd)`）；
- 这类命中从“静态模式角度”并非错误，但对 skill 风险评估来说需要进一步区分“引用示例”与“真实 helper 实现”。

### 4.3 `PERSISTENCE_MECHANISM`
当前 **21** 次命中。

主要剩余模式：

- reference/security 文档中列出 `systemd`、PM2、Kubernetes、launch config 作为审计对象；
- 这说明未来需要引入**path-aware / content-role-aware**判断，而不仅仅是关键词。

---

## 5. 建议的 Round 2 方向

### 方向 A：Path-aware tuning
对不同路径角色做差异化处理，例如：

- `SKILL.md`
- `scripts/`, `bin/`, `hooks/`
- `references/`, `examples/`, `docs/`
- `LICENSE*`

建议：

- 对 `references/` 与 `examples/` 中的高噪声规则做降级或特殊判定；
- 对 `scripts/` 与 `hooks/` 保持高敏感度。

### 方向 B：Instruction-vs-Reference 区分
增加“这是在**执行指令**，还是在**解释/引用/教学**”的区分特征，例如：

- imperative / operational tone
- first-party action intent
- quoted code example / anti-pattern example
- “MUST NOT / avoid / audit for / search for” 之类的防御性上下文

### 方向 C：Correlated scoring
将单条弱信号转为组合裁决：

- 单独出现 `.env` → 弱信号
- 单独出现 `requests.post` → 弱信号
- `.env` + outbound + script/helper path → 强信号

这会比当前单规则直接拉高 severity 更稳健。

---

## 6. 本轮结论

Round 1 已经证明 baseline 驱动的误报治理是有效的：

- finding 总量从 **1376** 降到 **429**；
- `safe` 样本从 **79** 提升到 **134**；
- 最主要的外传类噪声已被大幅压缩；
- 当前下一轮最值得优化的目标是：
  1. `SECRET_PATH_ACCESS`
  2. `DANGEROUS_SHELL_EXEC`
  3. `PERSISTENCE_MECHANISM`

建议下一步直接进入 **Round 2 path-aware tuning**。
