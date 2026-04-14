# SkillLint CLI 开发计划（v0.1 / 状态刷新）

- **项目**：SkillLint
- **日期**：2026-04-14
- **目标**：先交付一个可用的 CLI 工具，对单个 skill 输入进行解析、扫描、归类与报告输出。
- **相关文档**：
  - `docs/skill-security-threat-research-report.md`
  - `docs/skilllint-threat-taxonomy.md`
  - `docs/skilllint-detector-architecture.md`
  - `docs/skilllint-report-format.md`

---

## 0. 当前状态回顾

原始 v0.1 计划中的大部分主线能力已经实现，本文件现在同时承担两种作用：

1. 记录最初的 CLI 设计目标；
2. 标记这些目标当前是否已经落地，以及还有哪些尚未完成。

### 已实现的核心能力

- `skilllint scan <target>`
- `skilllint profiles`
- `skilllint evaluate-golden`
- 输入类型：
  - 本地目录
  - 本地 zip
  - 远程 URL
  - git repo URL
- 输出：
  - JSON
  - Markdown
  - SARIF 2.1.0
  - console summary
- 自动中英文 Markdown 报告
- 文件/行号/snippet 级 evidence
- 四类检测引擎：
  - package
  - regex
  - semantic（本地 + 可选 LLM）
  - dataflow
- golden labeled subset 与评估命令
- correlation scoring / aggregate score
- GitHub Actions / manifest / Dockerfile 风险检测
- Python / shell / JS/TS dataflow 检测

### 尚未实现或只实现了基础版的内容

- 更丰富的 LLM 多阶段 triage / consensus / budget policy
- external custom rule packs
- cross-skill / reputation 分析
- 更完整的 SARIF taxonomy component 建模
- `fail-on` 风险阈值控制
- HTML / PDF 报告制品
- 复杂运行时沙箱执行

---

## 1. 产品目标

SkillLint 的第一阶段目标是：

> **把一个 skill 样本（zip、目录、URL 等）解析为统一包结构，使用多种检测引擎对其进行安全分析，并输出机器可读结果与人类可读报告。**

### 本阶段必须满足的要求

1. **输入形式多样**
   - 本地目录
   - 本地 zip 包
   - 远程 URL（优先支持 zip / git repo / raw archive）
   - 后续可扩展：GitHub repo shorthand、marketplace item、stdin manifest

2. **输出双格式**
   - **规范化机器格式**：JSON（现已支持 SARIF）
   - **人类详细报告**：Markdown / 终端 summary
   - 报告语言根据 skill 的主要语言自动选择：**中文或英文**

3. **定位到原始文件位置**
   - findings 必须尽量包含：
     - 文件路径
     - 行号 / 行区间
     - snippet
     - rule_id
     - taxonomy code

4. **多引擎检测**
   - regex / signature
   - semantic（含 LLM）
   - dataflow
   - package / structure
   - 后续可扩展：binary、YARA、cross-skill、reputation

5. **基于 taxonomy 输出风险评估**
   - 每个 finding 映射到：
     - primary taxonomy
     - related taxonomy
     - confidence
     - severity
     - remediation

---

## 2. 非目标（v0.1 暂不做）

以下能力先不作为 v0.1 必交：

- 完整 IDE / GUI
- 在线托管服务
- 全量 marketplace 扫描平台
- 复杂运行时沙箱执行
- 自动修复 skill
- 多 skill 交叉关联分析的完整版本
- 完整 HTML / PDF 多报告制品矩阵

这些可在 v0.2+ 逐步补齐。

---

## 3. 交付物范围

v0.1 建议交付以下内容：

### 3.1 CLI 命令

```bash
skilllint scan <target>
```

支持：
- `skilllint scan ./my-skill`
- `skilllint scan ./my-skill.zip`
- `skilllint scan https://example.com/skill.zip`
- `skilllint scan https://github.com/org/repo`

建议参数（按当前已实现能力刷新）：

```bash
skilllint scan <target> \
  --format json|markdown|both|sarif|all \
  --output ./out \
  --lang auto|zh|en \
  --profile balanced|strict|marketplace-review|ci \
  --use-llm \
  --llm-base-url https://endpoint/v1 \
  --llm-api-key sk-... \
  --llm-model gpt-5.4 \
  --use-dataflow
```

当前实际还支持：

- `--config`
- `--enable-rule`
- `--disable-rule`
- `--enable-taxonomy`
- `--disable-taxonomy`
- `--llm-debug`

### 3.2 输出产物

- `result.json`：机器可读
- `report.md`：人类可读
- `result.sarif.json`：SARIF 2.1.0
- 终端 summary：简洁概览

### 3.3 检测引擎（第一批）

1. **Regex Engine**
   - 高风险命令
   - 外传模式
   - 直接 prompt injection 高危措辞
   - 敏感路径
   - symlink / hidden / binary / suspicious URL

2. **Package Engine**
   - skill 结构识别
   - manifest / `SKILL.md` / helper / binaries / hooks
   - 压缩包、隐藏文件、symlink、外链、安装链
   - `package.json` / `requirements*.txt` / `pyproject.toml`
   - GitHub Actions workflow 风险
   - Dockerfile bootstrap 风险

3. **Semantic Engine**
   - 非 LLM 规则语义层（上下文窗口 + 规则归纳）
   - LLM 语义审查层（降低误报漏报）

4. **Dataflow Engine**
   - 首批聚焦 Python / Shell（现已扩展到 JS/TS）
   - source → sink：
     - env/file/history -> network
     - user input -> exec/subprocess/eval

---

## 4. 核心设计原则

### 4.1 Normalize First
不论输入是 zip、目录还是 URL，先转换成统一的“工作区 skill 包”。

### 4.2 Engine Separation
检测引擎彼此独立，统一输出 finding，再交给 taxonomy mapper 和 report renderer。

### 4.3 Evidence First
每条 finding 都必须尽量给出证据；没有证据的语义判断应降低置信度。

### 4.4 LLM as Analyzer, not Oracle
LLM 用于**增强语义分析与 triage**，不是唯一判断来源。最终应由规则、结构、数据流和 LLM 共同给结论。

### 4.5 Reproducible Reports
相同输入与配置应尽量产生稳定结果；LLM 分析当前已保留 model / debug metadata（显式开启时），后续再完善 prompt budget 与 reasoning 摘要记录。

---

## 5. 架构草案

```text
Input Resolver
  ├─ local dir
  ├─ zip archive
  └─ remote url/git
        ↓
Workspace Normalizer
        ↓
Package Inspector
        ↓
Engines
  ├─ regex
  ├─ package
  ├─ semantic
  └─ dataflow
        ↓
Finding Aggregator
        ↓
Taxonomy Mapper
        ↓
Risk Scorer
        ↓
Output Renderers
  ├─ JSON
  ├─ Markdown / Console
  └─ SARIF
```

---

## 6. 目录结构建议

```text
src/skilllint/
  cli.py
  config.py
  models.py
  core/
    scanner.py
    workspace.py
    findings.py
  inputs/
    resolver.py
    download.py
    unpack.py
  engines/
    base.py
    regex_engine.py
    semantic_engine.py
    dataflow_engine.py
    package_engine.py
  taxonomy/
    mapper.py
    codes.py
  reporting/
    json_renderer.py
    markdown_renderer.py
    console_renderer.py
    sarif_renderer.py
  rules/
    regex/
    semantic/
    package/
    dataflow/
  utils/
    paths.py
    language.py
    snippets.py
    hashing.py
```

---

## 7. 输入处理设计

### 7.1 支持的 target 类型

| 类型 | 识别方式 | 处理方式 |
|---|---|---|
| 本地目录 | `Path.is_dir()` | 直接复制/挂载到工作区 |
| 本地 zip | `.zip` / mime | 解压到工作区 |
| HTTP/HTTPS URL | `http://` / `https://` | 下载到缓存后再解包/clone |
| GitHub/Git URL | `.git` / github repo url | shallow clone |

### 7.2 统一工作区
每次扫描创建：

```text
.skilllint-work/scan-<id>/
  original/
  normalized/
  extracted/
  metadata.json
```

### 7.3 规范化要求
- 保留原始相对路径
- 记录来源 URL / hash / 下载时间
- zip 解包后保留映射关系
- findings 中引用**归一化路径 + 原始路径**

---

## 8. 检测引擎设计

### 8.1 Regex Engine

#### 目标
低成本、高确定性地识别显著风险。

#### 第一批规则建议
- `curl|bash`, `wget|sh`, `bash -c`
- `preinstall`, `postinstall`
- `requests.post`, `curl -X POST`, `upload`, `webhook`
- `~/.ssh`, `.env`, `authorized_keys`, credential-like paths
- `before responding`, `do not mention`, `always do this`
- `os.system`, `subprocess(...shell=True)`, `eval`, `exec`
- suspicious URLs：pastebin / rentry / ghostbin / raw installers
- persistence：`crontab`, `systemd`, `.bashrc`, `launchd`

#### 输出
- exact match span
- matched pattern
- candidate taxonomy

### 8.2 Package Engine

#### 目标
从包结构层发现风险，而不是只看文本内容。

#### 检测对象
- `SKILL.md`
- manifest/frontmatter
- hooks/commands
- helper scripts
- binaries / archives
- hidden files
- symlinks
- nested skills
- external references / download instructions

#### 典型能力
- 判断 skill 主要语言
- 判断 skill 结构是否合法/完整
- 定位 nested skill
- 发现权限声明与结构不一致
- 检测 lifecycle script / remote dependency
- 检测 workflow trigger / permissions / unpinned actions
- 检测 Dockerfile remote bootstrap

### 8.3 Semantic Engine

#### 目标
降低简单规则的误报漏报，识别“伪装成正常流程”的恶意意图。

#### 两层实现

##### 第一层：轻量语义分析
- 上下文窗口归纳
- instruction priority 模式
- exfil masquerading（备份/审计/支持）
- trigger hijacking / over-broad description

##### 第二层：LLM 分析
- 对候选高风险片段做弹性语义判断
- 输出 structured finding
- 当前实现为：LLM 输出 plain-language semantic label，由本地映射到 taxonomy / confidence / remediation
- 支持按预算分段分析，而非全文无差别送模型

#### LLM 使用原则
- 只分析必要片段，避免 token 浪费
- 保存 prompt metadata，保证可审计
- 允许关闭 LLM，退化到纯静态模式

### 8.4 Dataflow Engine

#### 目标
识别 source→sink 风险链。

#### v0.1 范围
- Python AST taint tracking
- Shell heuristic dataflow
- JS/TS heuristic dataflow

#### 首批 source
- env vars
- sensitive files
- user-provided params
- conversation/history placeholders

#### 首批 sink
- network send
- subprocess / shell execution
- eval/exec
- file write to sensitive locations

---

## 9. 报告与输出设计

### 9.1 机器可读输出

首选 JSON，后续扩展 SARIF。当前已支持 JSON + SARIF。

建议字段：

```json
{
  "scan_id": "...",
  "target": "...",
  "normalized_target_type": "directory",
  "language": "zh",
  "summary": {
    "risk_level": "high",
    "finding_count": 12,
    "critical": 1,
    "high": 3,
    "medium": 5,
    "low": 3
  },
  "findings": []
}
```

### finding 字段
- `id`
- `rule_id`
- `title`
- `severity`
- `confidence`
- `primary_taxonomy`
- `related_taxonomy`
- `secondary_tags`
- `file`
- `line_start`
- `line_end`
- `snippet`
- `engine`
- `explanation`
- `remediation`

### 9.2 人类报告

#### 语言策略
- `lang=auto` 时，检测 skill 主要语言：
  - 中文占优 → 中文报告
  - 其他 → 英文报告

#### 报告内容
- 概览摘要
- 风险分级统计
- taxonomy 分布
- 关键高危问题 Top N
- 每个 finding 的位置、证据、原因、建议
- 附录：扫描配置、LLM 使用情况、输入来源

当前 Markdown 报告已实现：

- overview 表格
- severity summary
- taxonomy distribution
- top findings
- per-finding structured detail tables

---

## 10. 定位能力设计

为了满足“能定位到 skill 原始文件中的位置”，需要：

1. 文件按文本行号建索引；
2. regex finding 输出具体 span / 行号；
3. semantic finding 至少回溯到片段来源范围；
4. dataflow finding 给出 source/sink 所在文件与行号；
5. zip / URL 输入保留 `original_path -> normalized_path` 映射。

---

## 11. 风险评分设计（v0.1 简版）

### 输入
- severity baseline
- confidence
- primary taxonomy
- source→sink 是否闭环
- 是否涉及敏感文件 / 网络外发 / 持久化 / CI

### 输出
- `info/low/medium/high/critical`
- overall skill verdict：
  - `safe`
  - `suspicious`
  - `malicious`
  - `needs_review`

当前已实现：

- `risk_level`
- `score_risk_level`
- `verdict`
- `base_score`
- `correlation_score`
- `aggregate_score`
- `correlation_count`
- `distinct_files`
- `distinct_taxonomies`

---

## 12. 开发里程碑

### Milestone 0：项目初始化 ✅
- 目录结构
- `pyproject.toml`
- 基础 CLI 入口
- 默认配置
- README / LICENSE / docs

### Milestone 1：输入解析 + Package Engine ✅
- 目录 / zip / URL 支持
- 统一工作区
- 结构识别
- hidden/binary/symlink/basic manifest 检查

已超出原计划范围：
- git repo URL 支持
- manifest / workflow / Dockerfile 风险检测

### Milestone 2：Regex Engine + JSON 输出 ✅
- 首批 20~40 条高价值规则
- finding schema
- taxonomy mapper v0
- JSON 输出

### Milestone 3：Markdown 报告 + 自动中英文 ✅
- 报告语言 auto
- 控制台 summary
- 详细报告模板

已超出原计划范围：
- Markdown 报告结构化增强
- SARIF 输出

### Milestone 4：Semantic Engine（无 LLM + LLM）✅
- 基于片段的语义分析
- LLM 审查与 triage
- 误报压缩

当前仍待增强：
- richer multi-pass LLM workflow
- 更系统的 budget / consensus 策略

### Milestone 5：Dataflow Engine ✅
- Python taint
- Shell heuristics
- source→sink findings

已超出原计划范围：
- JS/TS dataflow
- 更多 Python / HTTP client / async sink 覆盖

### Milestone 6：测试与样本基线 ✅（基础版）
- 对 `examples/` 与 `examples/zh-community/` 建基线
- 生成 golden set
- 误报/漏报分析

当前已落地：
- golden labeled subset
- `evaluate-golden`
- rule / taxonomy precision-recall 风格评估
- 多轮 false-positive triage 文档

当前仍待增强：
- 更大的真实世界 baseline 回归
- detector-level regression dashboard

---

## 13. 测试策略

### 13.1 单元测试
- 输入识别
- 解压与目录规范化
- 行号映射
- rule matcher
- taxonomy mapper
- report language selector

### 13.2 集成测试
- 对单个 skill 目录扫描
- 对 zip 扫描
- 对 URL 扫描
- 输出 JSON / Markdown / SARIF

### 13.3 样本测试
- 使用 `examples/` 和 `examples/zh-community/`
- 建立：
  - benign set
  - suspicious set
  - malicious-like set
  - edge-case set

---

## 14. 风险与难点

1. **输入异构**：不同 skill 仓库结构差异大；
2. **定位精度**：语义分析往往难给精确行号；
3. **LLM 成本与稳定性**：需限制预算并保留可重复性；
4. **误报/漏报平衡**：不能只靠 regex；
5. **中英文报告切换**：需要较稳定的语言判断逻辑；
6. **URL 来源可信度**：下载、缓存、hash、重复扫描需统一管理。

---

## 15. v0.1 推荐技术栈

- **语言**：Python 3.11+
- **CLI**：Typer
- **数据模型**：Pydantic
- **配置**：TOML / YAML
- **终端展示**：Rich
- **模板**：当前 Markdown 渲染器已可用；如后续报告复杂度继续提升，可再考虑 Jinja2
- **测试**：Pytest
- **压缩/下载**：标准库 + `httpx`
- **LLM 接口**：先抽象 provider adapter，首批支持 OpenAI-compatible

---

## 16. 本文档之后的直接动作

原始计划中的“直接动作”已经完成。当前建议转为 v0.2 前置项：

1. 扩大真实样本 baseline / regression 评估；
2. 设计 external custom rule pack / plugin 机制；
3. 增强 richer LLM semantic workflow；
4. 提升 SARIF taxonomy component 与 ecosystem 集成能力；
5. 探索 cross-skill / reputation 分析。
