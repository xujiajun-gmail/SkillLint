# SkillLint Detector Architecture

- 项目：SkillLint
- 日期：2026-04-14
- 状态：Implemented Baseline

## 1. 目标

本文件描述 SkillLint 当前检测器（detector / engine）体系的职责边界、输入输出、实现方法与已覆盖能力，方便：

1. 新增规则或引擎时保持设计一致；
2. 理解 `rule catalog` 与 `engine logic` 的分层；
3. 为后续 LLM、多阶段裁决、误报治理和基线评估提供统一说明。

---

## 2. 检测器总览

SkillLint 当前由 4 类主检测器组成：

| Engine | 主要作用 | 当前实现 |
|---|---|---|
| `package` | 审计 skill 包结构、分发载荷、workflow/manifest 风险 | 已实现 |
| `regex` | 用高置信模式快速命中已知危险签名 | 已实现 |
| `semantic` | 做跨短语、跨上下文的语义级判断 | 已实现 |
| `dataflow` | 做 source-to-sink 风险传播分析 | 已实现 |

此外，`semantic` 引擎可选接入：

| 组件 | 作用 |
|---|---|
| `llm_analyzer` | 对已挑选的可疑片段做弹性语义复核，并映射回本地 taxonomy/rule 元数据 |

---

## 3. 规则层与执行层分工

SkillLint 采用：

```text
结构化规则目录 + 引擎执行逻辑
```

其中：

- `src/skilllint/rules/*/rules.yaml`：
  - 提供 `rule_id / severity / taxonomy / explanation / remediation`
- `src/skilllint/engines/*.py`：
  - 提供“怎么检测”的逻辑

这种设计的好处：

1. 规则元数据统一维护；
2. 报告、SARIF、JSON、profile 都能复用相同 rule catalog；
3. 引擎可独立演进，而不破坏对外稳定的 `rule_id`。

---

## 4. Package Engine

文件：`src/skilllint/engines/package_engine.py`

### 4.1 检测目标

`package` 引擎不做代码语义分析，而是做**分发层 / 包结构层**安全审计。

它主要回答：

- 这个 skill 包里带了什么？
- 有没有隐藏、自动执行、供应链、持久化相关载荷？

### 4.2 已覆盖能力

- `SKILL.md` 缺失 / 多个 `SKILL.md`
- symlink
- 隐藏文件
- 嵌套 archive
- binary artifact
- install/bootstrap script
- system startup artifact
- CI workflow 文件存在
- `package.json` lifecycle script
- `package.json` 远程 / VCS 依赖
- `requirements*.txt` 直链依赖
- `pyproject.toml` 远程依赖
- GitHub Actions：
  - unpinned action
  - dangerous trigger
  - elevated permissions
- Dockerfile：
  - remote `ADD`
  - `curl|wget | sh/bash`

### 4.3 适用场景

- skill marketplace 审核
- zip / repo / URL 下载内容审查
- 供应链与自动化工作流初筛

---

## 5. Regex Engine

文件：`src/skilllint/engines/regex_engine.py`

### 5.1 检测目标

`regex` 引擎用于快速命中：

- 明确、稳定、高置信的危险模式
- 已知 exploit primitive
- 易于描述且误报相对可控的文本签名

### 5.2 典型覆盖

- `curl | sh`
- prompt injection 优先级覆盖
- secret path access
- shell / eval / `shell=True`
- reverse shell
- destructive file operation
- remote instruction fetch
- CI untrusted context prompt

### 5.3 适用边界

适合：

- 明显模式
- 高性能大批量扫描

不适合：

- 需要上下文理解的隐蔽语义
- 需要 source-to-sink 传播的场景

---

## 6. Semantic Engine

文件：`src/skilllint/engines/semantic_engine.py`

### 6.1 检测目标

`semantic` 引擎负责：

- 发现不是单个关键词就能说明的问题
- 判断“组合语义”是否构成风险
- 为 LLM 二次分析挑选候选片段

### 6.2 当前实现方法

- keyword groups
- 语义规则组合（`all_of_groups / any_of_groups`）
- suppression heuristics
  - 防止 threat-model / 文档说明类文本被误判
- permission drift 等复合逻辑

### 6.3 LLM 路径

可选启用 `--use-llm`：

- 仅分析已筛出的少量候选片段
- LLM 输出 plain-language semantic labels
- 本地代码把 label 映射为：
  - `rule_id`
  - `taxonomy`
  - `title`
  - `remediation`

这避免了把内部 taxonomy 编码直接暴露给外部模型。

---

## 7. Dataflow Engine

文件：`src/skilllint/engines/dataflow_engine.py`

### 7.1 检测目标

`dataflow` 引擎关注：

```text
敏感 source  ->  危险 sink
```

比 regex 更重、比完整静态分析更轻，属于实用型 source-to-sink 检测。

### 7.2 当前语言覆盖

#### Python
- source
  - `os.getenv`
  - `os.environ[...]`
  - `.env` / `.ssh` / `id_rsa` / `.npmrc`
  - `Path(...).read_text()`
- network sink
  - `requests.*`
  - `httpx.*`
  - `aiohttp.*`
  - `.request(...)`
- exec sink
  - `subprocess.*`
  - `os.system`
  - `os.popen`
  - `eval` / `exec`
  - `asyncio.create_subprocess_shell`

#### Shell
- secret-like source + network sink
- variable interpolation + exec primitive

#### JS / TS
- source
  - `process.env`
  - `Deno.env.get`
  - `Bun.env`
  - `fs.readFileSync(".env")`
- network sink
  - `fetch`
  - `axios/got/request`
  - `http.request` / `https.request`
  - `client.post/put/request`
- exec sink
  - `exec`
  - `spawn`
  - `execa`

### 7.3 当前边界

当前不是完整跨文件静态分析器，因此仍有边界：

- 暂不做跨文件传播
- 暂不做完整 alias analysis
- 暂不做复杂对象字段级 taint lattice
- 偏向命中高风险、短路径的实用场景

---

## 8. 多引擎协同

SkillLint 当前大致流程：

1. `package`：先识别包层面的显著风险
2. `regex`：快速命中高置信签名
3. `semantic`：对文本和说明做语义级补充
4. `dataflow`：检查 source-to-sink
5. `correlation scoring`：汇总多 finding 的组合风险

这种设计使得：

- 单引擎即可给出结果；
- 多引擎一致命中时可提升总体风险可信度。

---

## 9. 后续演进建议

建议后续继续增强：

1. Python / JS 跨函数、跨文件 dataflow；
2. GitHub Actions 更深的 job/step 语义分析；
3. 自定义 rule pack / policy pack；
4. LLM 多阶段 triage 与 consensus；
5. detector-level precision / recall 基线面板。
