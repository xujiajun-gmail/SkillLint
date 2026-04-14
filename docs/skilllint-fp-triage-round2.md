# SkillLint False-Positive Triage — Round 2 (Path-Aware Tuning)

- 项目：SkillLint
- 日期：2026-04-14
- 语料：`examples/` + `examples/zh-community/`
- 样本数：200
- Profile：`balanced`
- 目标：通过 **path-aware rule filtering**，继续压低 `references/`、`examples/`、`templates/`、`api/`、`docs/` 等文档型路径带来的误报。

---

## 1. Round 1 之后剩余的主要问题

Round 1 后，baseline 已从 `1376` findings 降到 `429`，但仍存在明显噪声：

- `SECRET_PATH_ACCESS`: **204**
- `DANGEROUS_SHELL_EXEC`: **27**
- `PERSISTENCE_MECHANISM`: **21**
- `SEMANTIC_PERMISSION_DRIFT`: **25**

抽样发现，这些剩余误报中相当一部分并非来自真正的 skill 行为描述或 helper 脚本，而是来自：

- `references/**`
- `examples/**`
- `templates/**`
- `api/**`
- `docs/**`

典型模式包括：

1. reference/security 文档在解释 `.env`、`exec()`、`systemd`、webhook 等概念；
2. skill 打包了大量官方文档镜像或参考资料；
3. 这些文本本身是“说明/教学/反例”，而不是当前 skill 的真实执行逻辑。

---

## 2. Round 2 实现内容

### 2.1 规则级 path-aware 过滤能力

在规则模型中新增：

- `path_include_globs`
- `path_exclude_globs`

并让 `regex` / `semantic` 引擎在规则执行前判断当前文件路径是否适用该规则。

### 2.2 对高噪声 regex 规则加路径排除

以下规则新增 path exclusion：

- `SECRET_PATH_ACCESS`
- `NETWORK_EXFIL_SEND`
- `DANGEROUS_SHELL_EXEC`
- `PERSISTENCE_MECHANISM`
- `REVERSE_SHELL_PATTERN`

排除目录：

- `references/**`
- `examples/**`
- `templates/**`
- `api/**`
- `docs/**`

### 2.3 对部分 semantic 规则加路径排除

以下规则新增 path exclusion：

- `SEMANTIC_EXFIL_MASQUERADE`
- `SEMANTIC_HIDDEN_BEHAVIOR`

### 2.4 对 `SEMANTIC_PERMISSION_DRIFT` 加路径收缩

`SEMANTIC_PERMISSION_DRIFT` 改为仅默认应用于：

- `SKILL.md`
- `**/SKILL.md`

这样可以避免 reference 文档中的“只读/写权限”教学内容被误当成实际 capability drift。

---

## 3. Round 2 结果

重新生成 baseline 后：

- `total_findings`: **210**
- `malicious`: **6**
- `suspicious`: **46**
- `needs_review`: **5**
- `safe`: **143**

### 与 Round 1 对比

| 指标 | Round 1 | Round 2 | 变化 |
|---|---:|---:|---:|
| Total findings | 429 | 210 | **-51.0%** |
| `SECRET_PATH_ACCESS` | 204 | 95 | **-53.4%** |
| `DANGEROUS_SHELL_EXEC` | 27 | 5 | **-81.5%** |
| `SLT-B01` | 231 | 97 | **-58.0%** |
| `safe` | 134 | 143 | **+9** |

### 与 Round 0 对比

| 指标 | Round 0 | Round 2 | 变化 |
|---|---:|---:|---:|
| Total findings | 1376 | 210 | **-84.7%** |
| `SLT-B01` | 1113 | 97 | **-91.3%** |
| `SEMANTIC_EXFIL_MASQUERADE` | 508 | 2 | **-99.6%** |
| `NETWORK_EXFIL_SEND` | 156 | 0 | **-100%** |

> 注：`NETWORK_EXFIL_SEND` 在当前 Round 2 baseline 中已降到 0，说明“文档 URL / 参考说明 = 外传”的主要误报已基本压下去。

---

## 4. 典型样本变化

### `examples/openai/security-best-practices`
- Round 1: **64 findings**, `critical`
- Round 2: **2 findings**, `high`

当前仅剩：
- `INSTALL_LIFECYCLE_SCRIPT` x2

说明：原来几乎全部来自 reference security 文档中的教学/反例文本，path-aware 过滤后大量消失。

### `examples/openai/cloudflare-deploy`
- Round 1: **50 findings**, `critical`
- Round 2: **6 findings**, `critical`

剩余规则更接近真正值得审查的内容：
- `INSTALL_CURL_PIPE_SHELL`
- `SYSTEM_PROFILE_MODIFICATION`
- `DESTRUCTIVE_FILE_OPERATION`
- `TRIGGER_HIJACK_ANY_TASK`
- `SUSPICIOUS_DOWNLOAD_HOST`

### `examples/antfu/turborepo`
- Round 1: **59 findings**, `high`
- Round 2: **25 findings**, `high`

当前几乎全部集中在：
- `SECRET_PATH_ACCESS`

这说明下一轮的主要问题已经从“reference/docs 大面积噪声”收敛为“某几个具体规则在 `SKILL.md` 内仍然偏敏感”。

---

## 5. Round 2 结论

Round 2 证明 path-aware filtering 非常有效：

1. 对文档型 skill / reference-heavy skill 的误报压制非常明显；
2. 规则告警更集中于真正需要继续调优的少数规则；
3. baseline 已从“全局过噪”进入“少数规则精调阶段”。

当前最值得进入 Round 3 的目标：

- `SECRET_PATH_ACCESS`
  - 尤其是 `SKILL.md` 内讨论 `.env` / credentials / cache inputs 的正常说明；
- `SUSPICIOUS_DOWNLOAD_HOST`
  - 需要区分普通源码/raw 文档链接 vs 真正可疑分发链；
- `TRIGGER_HIJACK_ANY_TASK`
  - 需要更语义化地区分“广覆盖专业技能”与“恶意泛触发描述”。

---

## 6. 推荐下一步

进入 **Round 3 context-aware tuning**：

- 引入“defensive / instructional / anti-pattern example”上下文识别；
- 对 `SECRET_PATH_ACCESS` 做更细的防御性语境豁免；
- 逐步把 path-aware 扩展成 `path + content role + correlation` 的联合裁决。
