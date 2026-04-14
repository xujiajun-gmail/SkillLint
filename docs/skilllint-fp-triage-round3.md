# SkillLint False-Positive Triage — Round 3 (Context-Aware Tuning)

- 项目：SkillLint
- 日期：2026-04-14
- 语料：`examples/` + `examples/zh-community/`
- 样本数：200
- Profile：`balanced`
- 目标：在 Round 2 path-aware 基础上，引入更细的 **context-aware suppression**，区分真实危险意图与防御性说明、安装指引、缓存配置、清理操作说明等正常内容。

---

## 1. Round 2 后剩余的主要噪声

Round 2 后 baseline 已降到：

- `total_findings`: **210**
- `safe`: **143**

但剩余噪声主要集中在几类“正常工程说明”上：

1. **环境文件配置说明**
   - 例如 Turborepo / Apify / Vercel skills 中关于 `.env`、`--env-file=.env`、`.npmrc`、cache inputs 的正当文档说明；
2. **清理安装 / 重装依赖**
   - 如 `rm -rf node_modules pnpm-lock.yaml` 这类常见 clean install 指令；
3. **平台特定术语误判**
   - 例如 `fsevents` 依赖名被误认为文件监控/监视能力；
4. **重复性同类命中**
   - 同一文件中多次重复出现 `.env`、相似 cleanup 命令，导致 finding 数量被放大。

---

## 2. Round 3 实现内容

### 2.1 Regex 规则支持 `max_matches_per_file`

在规则模型中新增：

- `max_matches_per_file`

用于限制同一规则在同一文件中的重复告警数量，避免“同类提示成片刷屏”。

### 2.2 `SECRET_PATH_ACCESS` 收缩到更强信号

`SECRET_PATH_ACCESS` 不再覆盖 `.env`，而只保留更强的高风险路径信号：

- `~/.ssh`
- `.ssh/`
- `authorized_keys`
- `id_rsa`
- `aws credentials`
- `.npmrc`
- `.pypirc`

并增加每文件上限。

### 2.3 拆分出新规则：`ENV_FILE_CREDENTIAL_REFERENCE`

新增中等风险规则：

- `ENV_FILE_CREDENTIAL_REFERENCE`
- taxonomy: `SLT-E01`
- severity: `medium`

用于承接 `.env` / `--env-file=.env` + `token/secret/password/api_key/...` 这类更常见、但不应直接升级为高风险外传链的情况。

这样做的效果是：

- `.env` 不再默认触发高危 `SLT-B01`；
- 仍然保留“环境文件承载凭证”这一安全提醒；
- 严重度更贴近真实风险。

### 2.4 Context-aware suppression

在 `regex` 引擎中新增语境抑制逻辑：

#### 针对环境文件/凭证类
当上下文更像以下情形时，抑制告警：

- defensive guidance：`must not`, `do not`, `avoid`, `anti-pattern`, `wrong`, `correct` 等；
- instructional usage：`usage`, `example`, `quick start`, `troubleshoot`, `cache`, `inputs`, `--env-file` 等；
- `.npmrc` 的配置/设置型说明。

#### 针对破坏性删除类
对以下常见工程性清理场景做抑制：

- `clean install`
- `reinstall`
- 删除 `node_modules`
- 删除 lockfile：`package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`

这些通常是安装迁移、缓存重建、包管理器切换的正常指令，而不是恶意破坏。

### 2.5 `FILE_MONITORING_OR_WATCHER` 调整

不再把 `fsevents` 依赖名本身当成 covert monitoring 信号，避免误伤包管理与构建文档。

---

## 3. Round 3 结果

重新生成 baseline 后：

- `total_findings`: **96**
- `malicious`: **6**
- `suspicious`: **40**
- `needs_review`: **6**
- `safe`: **148**

### 与 Round 2 对比

| 指标 | Round 2 | Round 3 | 变化 |
|---|---:|---:|---:|
| Total findings | 210 | 96 | **-54.3%** |
| `safe` | 143 | 148 | **+5** |
| `SECRET_PATH_ACCESS` | 95 | 3 | **-96.8%** |
| `DESTRUCTIVE_FILE_OPERATION` | 24 | 16 | **-33.3%** |
| `FILE_MONITORING_OR_WATCHER` | 6 | 0 | **-100%** |

### 与 Round 0 对比

| 指标 | Round 0 | Round 3 | 变化 |
|---|---:|---:|---:|
| Total findings | 1376 | 96 | **-93.0%** |
| `SLT-B01` | 1113 | 3 | **-99.7%** |
| `safe` | 79 | 148 | **+69** |

---

## 4. 典型样本变化

### `examples/antfu/turborepo`
- Round 2: `1` finding（`ENV_FILE_CREDENTIAL_REFERENCE`）
- 相比更早阶段的大量 `.env`/cache 配置告警，已大幅收敛

### `examples/apify/apify-ultimate-scraper`
- Round 3: `0` findings
- 原先主要来自 `.env` / token / usage 文档说明的误报，现已基本抑制

### `examples/antfu/pnpm`
- Round 3: `3` findings
- 剩余主要为：
  - `INSTALL_LIFECYCLE_SCRIPT`
  - 少量 `DESTRUCTIVE_FILE_OPERATION`
- 这比此前 19 条高噪声结果明显更接近可审查状态

---

## 5. 当前剩余最主要的规则

Round 3 后 top rules 为：

- `SEMANTIC_HIDDEN_BEHAVIOR`: 18
- `DESTRUCTIVE_FILE_OPERATION`: 16
- `SEMANTIC_PERMISSION_DRIFT`: 10
- `ENV_FILE_CREDENTIAL_REFERENCE`: 7
- `SUSPICIOUS_DOWNLOAD_HOST`: 7
- `INSTALL_CURL_PIPE_SHELL`: 6

这说明接下来最值得优化的是：

1. **`SEMANTIC_HIDDEN_BEHAVIOR`**
   - 区分“不要告诉用户实现细节/内部机制”与真实隐蔽恶意行为；
2. **`DESTRUCTIVE_FILE_OPERATION`**
   - 更精细地区分工程清理动作 vs 真正 destructive intent；
3. **`SUSPICIOUS_DOWNLOAD_HOST`**
   - 区分正常 raw content/reference link 与真正不可信分发链。

---

## 6. 本轮结论

Round 3 说明：

- `path-aware` 已经把“文件角色”问题压下去；
- `context-aware` 又进一步把“内容语境”问题压下去；
- baseline 现已从 1376 findings 收敛到 96 findings，进入更可控的规则精调阶段。

下一步建议进入 **Round 4 semantic/context refinement**，重点处理：

- `SEMANTIC_HIDDEN_BEHAVIOR`
- `DESTRUCTIVE_FILE_OPERATION`
- `SUSPICIOUS_DOWNLOAD_HOST`
