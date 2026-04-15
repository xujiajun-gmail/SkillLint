# SkillLint 核心代码阅读顺序建议

本文档帮助新读者快速理解 SkillLint 的主链路、模块分工与推荐阅读顺序。

---

## 一、建议先建立的整体心智模型

SkillLint 的主流程可以概括为：

1. **接收输入**
   - CLI / Web API 接收目录、zip、URL、git URL 等输入
2. **识别目标类型**
   - 判断输入是本地目录、压缩包、远程文件还是仓库 URL
3. **准备统一工作区**
   - 下载 / 解压 / clone / 拷贝到标准化目录
4. **运行多个检测引擎**
   - `package`
   - `regex`
   - `semantic`
   - `dataflow`
5. **统一 finding 结构**
   - taxonomy 映射
   - correlation 组合风险
   - summary / score 计算
6. **输出结果**
   - console
   - JSON
   - Markdown
   - SARIF
   - Web API / Web UI

如果先带着这个心智模型再看代码，会容易很多。

---

## 二、推荐阅读顺序

### 1. 先看统一数据模型

**推荐文件：**

- `src/skilllint/models.py`

**为什么先看这里：**

这是全项目最核心的“数据契约”。
只要理解了这些结构，后面看 scanner、engine、reporting 都会容易很多。

重点关注：

- `TargetInfo`
- `WorkspaceInfo`
- `Evidence`
- `Finding`
- `CorrelationHit`
- `ScanSummary`
- `ScanResult`

---

### 2. 再看 CLI 入口如何把用户输入翻译成扫描配置

**推荐文件：**

- `src/skilllint/cli.py`
- `src/skilllint/config.py`

**重点理解：**

- CLI 参数如何覆盖配置
- profile 如何生效
- 输出格式如何选择
- `scan` 和 `evaluate-golden` 两条入口分别做什么

**阅读目标：**

搞清楚：

> 用户输入是如何变成一个 `SkillLintConfig`，再进入扫描主链路的。

---

### 3. 看输入目标识别与工作区准备

**推荐文件：**

- `src/skilllint/inputs/resolver.py`
- `src/skilllint/core/workspace.py`

**这是最重要的基础设计之一。**

SkillLint 采用的是：

> **Normalize First（先归一化，再检测）**

也就是不管输入原本是什么，后续检测器看到的都只是统一的标准化目录。

重点关注：

- `resolve_target()`
- `prepare_workspace()`
- `_copy_directory()`
- `_extract_zip()`
- `_download_url()`
- `_clone_repo()`

**阅读目标：**

搞清楚：

> 为什么各个 engine 不需要关心输入原本是什么。

---

### 4. 再看扫描总编排

**推荐文件：**

- `src/skilllint/core/scanner.py`

这是全项目最关键的“总控层”。

重点关注：

- `SkillScanner.__init__`
- `SkillScanner.scan`
- `SkillScanner._run_engines`
- `SkillScanner._resolve_language`

**要重点理解的问题：**

- 各引擎为什么按固定顺序运行
- taxonomy 映射为什么放在这里统一做
- correlation 为什么是“第二层信号”
- summary / score breakdown 为什么放在所有引擎之后

**阅读目标：**

搞清楚：

> 一次扫描从开始到产出 `ScanResult` 的完整主链路。

---

## 三、检测引擎建议阅读顺序

建议按下面顺序看：

### 1. Package Engine

**文件：**

- `src/skilllint/engines/package_engine.py`

**适合先看原因：**

它最直观，主要关注“包里有什么”。

重点看：

- `run()`
- `_scan_package_json()`
- `_scan_python_dependency_manifest()`
- `_scan_pyproject()`
- `_scan_ci_workflow()`
- `_scan_dockerfile()`

你会看到 SkillLint 如何从：

- 隐藏文件
- 嵌套归档
- 二进制
- symlink
- install script
- lifecycle scripts
- remote dependency
- CI workflow
- Docker bootstrap

这些“包结构风险”中生成 finding。

---

### 2. Regex Engine

**文件：**

- `src/skilllint/engines/regex_engine.py`

**重点看：**

- `run()`
- `_is_context_suppressed()`

**核心理解点：**

- regex 引擎为什么快、稳定
- 为什么最容易误报
- suppression 是如何压制文档/说明类误报的

---

### 3. Semantic Engine

**文件：**

- `src/skilllint/engines/semantic_engine.py`

**重点看：**

- `run()`
- `_scan_text()`
- `_semantic_rule_match_range()`
- `_segment_ranges()`
- `_permission_drift_supported()`

**核心理解点：**

- semantic 不是简单 regex
- 它是“段落分片 + 关键词组共现 + 启发式压制”
- 它如何利用前序引擎的 seed findings
- permission drift 为什么要结合上下文和已有 finding 一起判断

---

### 4. LLM Analyzer

**文件：**

- `src/skilllint/engines/llm_analyzer.py`

**这部分建议在看完 semantic engine 后再看。**

重点关注：

- `LLMCandidate`
- `SemanticLabelSpec`
- `SEMANTIC_LABEL_SPECS`
- `LLMAnalyzer.analyze()`
- `_get_client()`
- `_analyze_candidate()`
- `_build_prompt()`
- `_dedupe_findings()`

**核心理解点：**

- 为什么 LLM 不直接扫全仓库
- 为什么先做本地筛选，再把候选片段送给 LLM
- 为什么外部模型返回的是 plain-language label，而不是直接返回 SkillLint taxonomy code

---

### 5. Dataflow Engine

**文件：**

- `src/skilllint/engines/dataflow_engine.py`

这是最“静态分析”味道的一部分。

建议分三层看：

1. `DataflowEngine.run()`
2. Python 路径：
   - `PythonTaintAnalyzer`
   - `_call_name()`
   - `_finding_from_call()`
3. Shell / JS 启发式路径：
   - `_scan_shell()`
   - `_scan_javascript()`
   - `_js_taint_*`

**核心理解点：**

- 为什么 Python 用 AST
- 为什么 shell / JS 先用轻量启发式
- SkillLint 为什么选“实用型 source -> sink”，而不是追求完整编译器级分析

---

## 四、规则与 taxonomy 怎么看

### 1. 规则仓库

**文件：**

- `src/skilllint/rules/repository.py`
- `src/skilllint/rules/selector.py`

**规则数据文件：**

- `src/skilllint/rules/regex/rules.yaml`
- `src/skilllint/rules/package/rules.yaml`
- `src/skilllint/rules/semantic/rules.yaml`
- `src/skilllint/rules/dataflow/rules.yaml`

**重点理解：**

- 为什么规则元数据和检测实现分离
- `RuleSelector` 如何对所有引擎统一做 include/exclude 裁剪

---

### 2. taxonomy 映射

**文件：**

- `src/skilllint/taxonomy/mapper.py`

虽然现在大多数规则在 catalog 中已经直接带 taxonomy，
但这里仍保留了兜底映射层，避免历史规则或特殊 finding 丢失分类。

---

## 五、评分与相关性建议重点看

**文件：**

- `src/skilllint/scoring.py`

这部分决定：

- finding 如何转换成 score
- correlation 如何放大组合风险
- 最终 verdict 如何产生

推荐重点阅读：

- `PATTERNS`
- `correlate_findings()`
- `build_summary()`
- `build_score_breakdown()`
- `_finding_score_contributions()`
- `_correlation_score()`
- `_verdict_from_signals()`

**核心理解点：**

- SkillLint 不是只看“最高 severity”
- 它还看：
  - 多信号组合
  - 多引擎交叉确认
  - 多 taxonomy 重叠
  - 仓库级高风险聚集

---

## 六、输出层怎么读

**推荐文件：**

- `src/skilllint/reporting/console_renderer.py`
- `src/skilllint/reporting/json_renderer.py`
- `src/skilllint/reporting/markdown_renderer.py`
- `src/skilllint/reporting/sarif_renderer.py`

建议顺序：

1. `json_renderer.py`
2. `console_renderer.py`
3. `markdown_renderer.py`
4. `sarif_renderer.py`

**原因：**

- JSON 最直接，几乎就是 `ScanResult`
- console 最薄
- Markdown 是人类可读报告主视图
- SARIF 是平台集成格式，结构最重

---

## 七、Web App 怎么读

### 后端

**推荐文件：**

- `src/app/schemas.py`
- `src/app/api.py`
- `src/app/service.py`
- `src/app/main.py`

建议顺序：

1. `schemas.py`
2. `api.py`
3. `service.py`
4. `main.py`

**核心理解点：**

- API 层只做 HTTP 参数接收与错误映射
- `ScanService` 才是真正复用 SkillScanner 的业务层
- Web 返回体为什么同时包含：
  - `scan_result`
  - `report_markdown`
  - `source_files`

---

### 前端

**推荐文件：**

- `src/app/static/index.html`
- `src/app/static/app.js`
- `src/app/static/styles.css`

建议重点看 `app.js` 的这些函数：

- `submitScan()`
- `setSourceType()`
- `renderReport()`
- `renderFindings()`
- `renderSourceViewer()`
- `scrollSourceToFinding()`
- `renderFindingFallback()`

**核心理解点：**

- UI 状态很少，逻辑都围绕一个扫描响应对象展开
- 点击 finding 如何驱动右侧源码区刷新
- 没有源码文件时为什么会退化成 fallback detail view

---

## 八、评估与基线功能怎么读

**推荐文件：**

- `src/skilllint/baseline.py`
- `src/skilllint/evaluation.py`

### baseline

解决的是：

> 当前规则在真实样本集上的“回归快照”是什么？

### golden evaluation

解决的是：

> 当前规则相对于人工标注约束，precision / recall 风格表现如何？

---

## 九、如果你时间有限，最小阅读路径

如果你只想在最短时间内建立全局理解，建议按这个顺序：

1. `src/skilllint/models.py`
2. `src/skilllint/config.py`
3. `src/skilllint/inputs/resolver.py`
4. `src/skilllint/core/workspace.py`
5. `src/skilllint/core/scanner.py`
6. `src/skilllint/engines/package_engine.py`
7. `src/skilllint/engines/regex_engine.py`
8. `src/skilllint/engines/semantic_engine.py`
9. `src/skilllint/engines/dataflow_engine.py`
10. `src/skilllint/scoring.py`
11. `src/skilllint/reporting/markdown_renderer.py`
12. `src/app/service.py`
13. `src/app/static/app.js`

---

## 十、如果你要改代码，建议从哪一层下手

### 想加新规则

先看：

- `src/skilllint/rules/*/rules.yaml`
- 对应 engine

### 想调误报

先看：

- `regex_engine.py` 的 suppression
- `semantic_engine.py` 的 suppression / 分段逻辑
- `package_engine.py` 的启发式条件

### 想调评分

先看：

- `src/skilllint/scoring.py`

### 想改 Web 展示

先看：

- `src/app/service.py`
- `src/app/static/app.js`
- `src/app/static/styles.css`

### 想接新的 LLM Provider

先看：

- `src/skilllint/config.py`
- `src/skilllint/engines/llm_analyzer.py`

---

## 十一、一句话总结

理解 SkillLint 的最好方式不是从某个 engine 孤立开始，而是沿着这条链路阅读：

> **输入识别 → 工作区归一化 → 多引擎扫描 → finding 统一化 → correlation/score → 报告与 Web 展示**

沿这条线读，最容易真正理解这个系统。
