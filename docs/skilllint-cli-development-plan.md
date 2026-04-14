# SkillLint CLI 开发计划（v0.1）

- **项目**：SkillLint
- **日期**：2026-04-13
- **目标**：先交付一个可用的 CLI 工具，对单个 skill 输入进行解析、扫描、归类与报告输出。
- **相关文档**：
  - `docs/skill-security-threat-research-report.md`
  - `docs/skilllint-threat-taxonomy.md`

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
   - **规范化机器格式**：JSON（后续可扩展 SARIF）
   - **人类详细报告**：Markdown / 终端富文本
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
- 完整 SARIF / HTML / PDF 多报告制品矩阵

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

建议参数：

```bash
skilllint scan <target> \
  --format json|markdown|both \
  --output ./out \
  --lang auto|zh|en \
  --profile strict|balanced|permissive \
  --use-llm \
  --llm-provider openai \
  --fail-on high
```

### 3.2 输出产物

- `result.json`：机器可读
- `report.md`：人类可读
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

3. **Semantic Engine**
   - 非 LLM 规则语义层（上下文窗口 + 规则归纳）
   - LLM 语义审查层（降低误报漏报）

4. **Dataflow Engine**
   - 首批聚焦 Python / Shell
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
相同输入与配置应尽量产生稳定结果；LLM 分析需保留 prompt budget、model、版本与 reasoning 摘要。

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
  └─ Markdown / Console
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
.work/scan-<id>/
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

## 8.1 Regex Engine

### 目标
低成本、高确定性地识别显著风险。

### 第一批规则建议
- `curl|bash`, `wget|sh`, `bash -c`
- `preinstall`, `postinstall`
- `requests.post`, `curl -X POST`, `upload`, `webhook`
- `~/.ssh`, `.env`, `authorized_keys`, credential-like paths
- `before responding`, `do not mention`, `always do this`
- `os.system`, `subprocess(...shell=True)`, `eval`, `exec`
- suspicious URLs：pastebin / rentry / ghostbin / raw installers
- persistence：`crontab`, `systemd`, `.bashrc`, `launchd`

### 输出
- exact match span
- matched pattern
- candidate taxonomy

## 8.2 Package Engine

### 目标
从包结构层发现风险，而不是只看文本内容。

### 检测对象
- `SKILL.md`
- manifest/frontmatter
- hooks/commands
- helper scripts
- binaries / archives
- hidden files
- symlinks
- nested skills
- external references / download instructions

### 典型能力
- 判断 skill 主要语言
- 判断 skill 结构是否合法/完整
- 定位 nested skill
- 发现权限声明与结构不一致

## 8.3 Semantic Engine

### 目标
降低简单规则的误报漏报，识别“伪装成正常流程”的恶意意图。

### 两层实现

#### 第一层：轻量语义分析
- 上下文窗口归纳
- instruction priority 模式
- exfil masquerading（备份/审计/支持）
- trigger hijacking / over-broad description

#### 第二层：LLM 分析
- 对候选高风险片段做弹性语义判断
- 输出 structured finding
- 判断 primary taxonomy / confidence / remediation
- 支持按预算分段分析，而非全文无差别送模型

### LLM 使用原则
- 只分析必要片段，避免 token 浪费
- 保存 prompt metadata，保证可审计
- 允许关闭 LLM，退化到纯静态模式

## 8.4 Dataflow Engine

### 目标
识别 source→sink 风险链。

### v0.1 范围
- Python AST taint tracking
- Shell heuristic dataflow

### 首批 source
- env vars
- sensitive files
- user-provided params
- conversation/history placeholders

### 首批 sink
- network send
- subprocess / shell execution
- eval/exec
- file write to sensitive locations

---

## 9. 报告与输出设计

## 9.1 机器可读输出

首选 JSON，后续扩展 SARIF。

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

## 9.2 人类报告

### 语言策略
- `lang=auto` 时，检测 skill 主要语言：
  - 中文占优 → 中文报告
  - 其他 → 英文报告

### 报告内容
- 概览摘要
- 风险分级统计
- taxonomy 分布
- 关键高危问题 Top N
- 每个 finding 的位置、证据、原因、建议
- 附录：扫描配置、LLM 使用情况、输入来源

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

---

## 12. 开发里程碑

## Milestone 0：项目初始化
- 目录结构
- `pyproject.toml`
- 基础 CLI 入口
- 默认配置
- README / LICENSE / docs

## Milestone 1：输入解析 + Package Engine
- 目录 / zip / URL 支持
- 统一工作区
- 结构识别
- hidden/binary/symlink/basic manifest 检查

## Milestone 2：Regex Engine + JSON 输出
- 首批 20~40 条高价值规则
- finding schema
- taxonomy mapper v0
- JSON 输出

## Milestone 3：Markdown 报告 + 自动中英文
- 报告语言 auto
- 控制台 summary
- 详细报告模板

## Milestone 4：Semantic Engine（无 LLM + LLM）
- 基于片段的语义分析
- LLM 审查与 triage
- 误报压缩

## Milestone 5：Dataflow Engine
- Python taint
- Shell heuristics
- source→sink findings

## Milestone 6：测试与样本基线
- 对 `examples/` 与 `examples/zh-community/` 建基线
- 生成 golden set
- 误报/漏报分析

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
- 输出 JSON / Markdown

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
- **模板**：Jinja2（报告渲染）
- **测试**：Pytest
- **压缩/下载**：标准库 + `httpx`
- **LLM 接口**：先抽象 provider adapter，首批支持 OpenAI-compatible

---

## 16. 本文档之后的直接动作

按当前计划，建议紧接着做：

1. 初始化 Python 包与 CLI 骨架；
2. 定义 finding schema 与 config schema；
3. 落第一个可运行的 `skilllint scan <target>`；
4. 先实现 Package Engine + Regex Engine；
5. 再接入 Markdown/JSON 双输出。
