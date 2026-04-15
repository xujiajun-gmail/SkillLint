# SkillLint Risk Flows 设计说明

## 1. 背景

SkillLint 的核心输出是 `findings`。每条 finding 用来回答：

- 哪条规则命中？
- 风险在哪个文件、哪一行？
- 严重级别、taxonomy、修复建议是什么？

但在实际审计中，单个 finding 往往不足以解释完整攻击路径。例如：

- `SKILL.md` 里要求信任 tool output；
- 同一段又要求把返回内容追加到 `MEMORY.md`；
- 这不是两个孤立问题，而是一条 “untrusted content → persistent memory” 链。

因此本轮新增了 `metadata.risk_flows`，用于从离散 findings 中归纳结构化风险链。

## 2. 输出位置

`risk_flows` 位于 JSON/SARIF 可消费的扫描结果 metadata 中：

```json
{
  "metadata": {
    "risk_flows": [
      {
        "id": "flow.slt-b04.instructions-to-persistent-memory",
        "title": "Instructions or tool output may persist into long-lived memory",
        "primary_taxonomy": "SLT-B04",
        "severity": "high",
        "file": "SKILL.md",
        "triggered_rule_ids": [
          "SEMANTIC_EMBEDDED_INSTRUCTION_FOLLOWING",
          "SEMANTIC_MEMORY_PERSISTENCE",
          "MEMORY_FILE_PERSISTENCE_WRITE"
        ],
        "evidence_refs": ["...finding id..."],
        "path_labels": ["runtime/tool content", "persistent memory file"],
        "finding_count": 3
      }
    ]
  }
}
```

## 3. 当前支持的 flow 类型

| Flow ID | 说明 | 主要 taxonomy |
|---|---|---|
| `flow.slt-b01.secret-to-egress` | secret / credential 流向网络外发点 | `SLT-B01` |
| `flow.slt-e01.secret-to-log` | secret / credential 流向 stdout 或日志 | `SLT-E01` |
| `flow.slt-a03.external-instructions-to-context` | 外部内容被当作 agent 指令上下文 | `SLT-A03` |
| `flow.slt-b04.instructions-to-persistent-memory` | 指令或 tool output 被写入长期记忆 | `SLT-B04` |
| `flow.slt-b02.tainted-delete-target` | 外部/污染参数控制破坏性删除目标 | `SLT-B02` |
| `flow.slt-c04.workspace-policy-poisoning` | skill 写入 `.env`、`.cursor/rules.mdc` 等工作区控制文件 | `SLT-C04` |

## 4. 为什么放在 metadata 而不是替代 findings？

这样设计有几个好处：

1. **兼容现有 schema**  
   下游工具依然可以只消费 `findings`，不会因为新增 flow 而破坏解析逻辑。

2. **保持 evidence-first**  
   flow 只引用已有 finding 的 `id`，不制造无法定位的新证据。

3. **便于 UI 渲染**  
   Web UI 可以先展示 flow，再通过 `evidence_refs` 跳转到对应 finding 和源码定位。

4. **便于后续扩展**  
   未来可以加入更复杂的跨文件 flow、LLM 辅助 flow 归纳、policy decision 等字段。

## 5. 实现位置

- Flow 构建逻辑：`src/skilllint/flows.py`
- 扫描主流程接入：`src/skilllint/core/scanner.py`
- 回归测试：`tests/unit/test_risk_flows.py`

当前实现是 deterministic 的规则后处理，不依赖 LLM。
