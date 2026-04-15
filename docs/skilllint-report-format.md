# SkillLint Report Format

- 项目：SkillLint
- 日期：2026-04-14
- 状态：Implemented Baseline

## 1. 目标

SkillLint 当前同时面向两类输出消费者：

1. **机器消费者**
   - CI
   - policy engine
   - SARIF / code scanning
   - 后续自动化处置
2. **人工消费者**
   - 安全审查人员
   - skill 作者
   - marketplace 审核人员

因此 SkillLint 同时输出：

- JSON
- Markdown
- SARIF

---

## 2. 输出文件

| 格式 | 默认文件 |
|---|---|
| JSON | `result.json` |
| Markdown | `report.md` |
| SARIF | `result.sarif.json` |

CLI 示例：

```bash
skilllint scan ./skill --format json
skilllint scan ./skill --format markdown
skilllint scan ./skill --format sarif
skilllint scan ./skill --format all
```

---

## 3. JSON 顶层结构

当前 `result.json` 顶层字段包括：

```json
{
  "scan_id": "...",
  "tool_version": "...",
  "target": {},
  "workspace": {},
  "language": "en",
  "summary": {},
  "findings": [],
  "metadata": {}
}
```

---

## 4. Summary 字段

`summary` 主要用于机器与人工快速理解整体风险：

```json
{
  "risk_level": "high",
  "score_risk_level": "high",
  "verdict": "suspicious",
  "finding_count": 7,
  "critical": 1,
  "high": 2,
  "medium": 3,
  "low": 1,
  "info": 0,
  "base_score": 48,
  "correlation_score": 20,
  "aggregate_score": 68,
  "correlation_count": 2,
  "distinct_files": 3,
  "distinct_taxonomies": 4
}
```

### 字段说明

- `risk_level`
  - 基于 finding severity 聚合得到的直观风险等级
- `score_risk_level`
  - 基于综合分数映射得到的风险等级
- `verdict`
  - 当前总体裁决：
    - `safe`
    - `needs_review`
    - `suspicious`
    - `malicious`
- `base_score`
  - finding 直接分数
- `correlation_score`
  - 多 finding 组合命中的附加分
- `aggregate_score`
  - 总分

---

## 5. Finding 结构

每条 finding 当前包含：

```json
{
  "id": "...",
  "rule_id": "DATAFLOW_SECRET_TO_NETWORK",
  "title": "Sensitive source flows to network sink",
  "severity": "critical",
  "confidence": "medium",
  "engine": "dataflow",
  "primary_taxonomy": "SLT-B01",
  "related_taxonomy": [],
  "secondary_tags": ["dataflow", "confidentiality", "script"],
  "explanation": "...",
  "remediation": "...",
  "evidence": {
    "file": "sync.py",
    "line_start": 4,
    "line_end": 4,
    "snippet": "..."
  },
  "metadata": {}
}
```

### 关键设计点

- `rule_id`
  - 稳定规则标识，用于 SARIF、策略开关、基线评估
- `engine`
  - 标识 finding 来自哪个检测器
- `primary_taxonomy`
  - SkillLint threat taxonomy 主分类
- `evidence`
  - 尽量定位到文件 / 行号 / 代码片段

---

## 6. Metadata 字段

`metadata` 当前会包含扫描上下文信息，例如：

- `profile`
- `source_language`
- `enabled_engines`
- `rule_catalog`
- `rule_filters`
- `correlation_hits`
- `risk_flows`
- `score_breakdown`
- `semantic_llm_status`

在启用 `--llm-debug` 时，还可能包含：

- `semantic_llm_debug`

> 注意：`semantic_llm_debug` 会包含原始 LLM 返回与片段内容，只应在调试时启用。

### `risk_flows`

`metadata.risk_flows` 是由 findings 后处理归纳出的攻击链/风险链视图。
它不会替代 `findings`，而是通过 `evidence_refs` 引用已有 finding，便于前端和外部系统展示“源 → 汇”的路径。

示例：

```json
{
  "id": "flow.slt-b04.instructions-to-persistent-memory",
  "title": "Instructions or tool output may persist into long-lived memory",
  "primary_taxonomy": "SLT-B04",
  "severity": "high",
  "file": "SKILL.md",
  "triggered_rule_ids": [
    "SEMANTIC_EMBEDDED_INSTRUCTION_FOLLOWING",
    "SEMANTIC_MEMORY_PERSISTENCE"
  ],
  "evidence_refs": ["...finding id..."],
  "path_labels": ["runtime/tool content", "persistent memory file"],
  "finding_count": 2
}
```

详细说明见：

- `docs/skilllint-risk-flows.md`

---

## 7. Markdown 报告

Markdown 报告面向人工阅读，当前特点：

- 自动根据 skill 主要语言输出中文或英文
- 展示 summary
- 按 finding 列出：
  - 风险等级
  - taxonomy
  - rule_id
  - 解释
  - 修复建议
  - 文件定位
  - 证据片段

适合：

- 人工复核
- issue / PR 评论
- marketplace 审核记录

---

## 8. SARIF

SARIF 说明见：

- `docs/skilllint-sarif-output.md`

SARIF 主要面向：

- GitHub code scanning
- 安全平台聚合
- CI 管道

---

## 9. 语言策略

SkillLint 当前报告语言策略：

- `--lang auto`
  - 自动探测 skill 主要语言
- `--lang zh`
  - 强制中文
- `--lang en`
  - 强制英文

这只影响人类可读报告语言，不影响 `rule_id`、taxonomy、JSON 结构。

---

## 10. 后续建议

建议后续继续增强：

1. 输出 JSON schema 文档；
2. 增加 finding fingerprint；
3. 增加 remediation priority；
4. 增加 baseline diff / regression report；
5. 增加 detector-level explanation block。
