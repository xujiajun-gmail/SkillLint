# SkillLint vs skill-safe Fixtures Coverage Report

> 基于当前主分支、`strict` profile 的一次对照盘点。  
> 目的不是追求与 `skill-safe` 一模一样的 taxonomy/decision，而是确认 SkillLint 是否已对这些已知风险模式形成有效检测覆盖。

## 1. 总体结论

当前 SkillLint 已对 `skill-safe` fixture 中的大部分核心风险模式形成覆盖，尤其是：

- manifest / plugin manifest 解析
- alignment / underdeclared behavior
- secret → log / secret → network
- tool output trust / memory persistence
- tainted delete target
- workspace poisoning
- hidden unicode / floating reference / identity mismatch

在当前 fixture 集中：

- 明显恶意或高危样例：已基本都能命中
- 正常/低风险基线样例：保持低噪声
- 尚未对齐 `skill-safe` 的部分：主要在 **flow 命名、policy decision 语义、diff/report 机制**，而不是基础检测缺失

## 2. 覆盖表

| Fixture | 当前 SkillLint 结果 | 覆盖判断 |
|---|---|---|
| `basic_skill` | 0 findings | 符合预期 |
| `credential_leak_skill` | `DATAFLOW_SECRET_TO_LOG` | 已覆盖 |
| `destructive_skill` | `DESTRUCTIVE_FILE_OPERATION`, `DATAFLOW_SHELL_TAINTED_DELETE_TARGET` | 已覆盖 |
| `alignment_skill` | manifest risky permission / startup hook / underdeclared network & shell / permission drift | 已覆盖 |
| `diff_case_v1` | 0 findings | 符合预期 |
| `diff_case_v2` | remote bootstrap + startup hook + risky permissions | 已覆盖 |
| `diff_flow_v1` | 0 findings | 符合预期 |
| `diff_flow_v2` | embedded instruction + memory persistence | 已覆盖 |
| `flow_context_skill` | embedded instruction + memory persistence | 已覆盖 |
| `flow_param_skill` | destructive chain + tainted delete target + shell permission | 已覆盖 |
| `memory_writer_skill` | memory persistence + memory file write | 已覆盖 |
| `network_skill` | local endpoint + metadata endpoint + network permission | 已覆盖 |
| `risky_skill` | prompt injection + secret path + hidden behavior + memory persistence + secret-to-network + startup hook + floating ref | 已覆盖 |
| `supply_chain_skill` | floating reference + hidden unicode marker | 已覆盖 |
| `trust_mismatch_skill` | identity mismatch | 已覆盖 |
| `workspace_poison_skill` | rules write + env write + workspace poisoning semantic | 已覆盖 |

## 3. 新增的结构化 flow 覆盖

本轮除 finding 外，还新增了 `metadata.risk_flows`，用于表达更高层次的攻击链：

- `flow.slt-b01.secret-to-egress`
- `flow.slt-e01.secret-to-log`
- `flow.slt-a03.external-instructions-to-context`
- `flow.slt-b04.instructions-to-persistent-memory`
- `flow.slt-b02.tainted-delete-target`
- `flow.slt-c04.workspace-policy-poisoning`

这使得 SkillLint 在表达能力上更接近 `skill-safe` 中强调的 “flow / chain” 视角，虽然 taxonomy 与 flow id 命名仍不同。

## 4. 仍与 skill-safe 存在的差异

### 4.1 taxonomy 不同

`skill-safe` 使用自己的 taxonomy（如 `CH-001` / `SC-004` / `AL-001`），  
SkillLint 使用自己的 taxonomy（如 `SLT-B01` / `SLT-C04` / `SLT-E03`）。

因此两者更适合按“风险语义是否覆盖”比较，而不是按 ID 一一对应。

### 4.2 policy / decision 模型不同

`skill-safe` 有更强的 admission / policy 风格输出，比如：

- allow / review / block
- allow_localhost / allow_memory_file_write 等策略开关
- diff 输出中的 decision drift

SkillLint 当前更偏向：

- finding + taxonomy + severity
- aggregate score / verdict
- correlation scoring

### 4.3 diff / explain / flow drift 机制尚未对齐

`skill-safe` 已有：

- `diff`
- `explain`
- flow drift

SkillLint 当前主线仍聚焦 **scan**，虽然已具备结构化 flow，但尚未形成完整的 diff / explain 体验。

## 5. 下一步建议

如果要继续向 `skill-safe` 的能力形态靠拢，下一阶段建议优先做：

1. **scan 结果中的 flow 进一步细化**
   - source node / sink node
   - blocked_by_policy
   - cross-file path

2. **增加 diff 模式**
   - old vs new skill 的 taxonomy drift
   - finding delta
   - flow delta

3. **引入 policy profile / gating**
   - fail-on threshold
   - allow_localhost / allow_memory_write 等细粒度策略

4. **补 explain 能力**
   - 将 findings + flows + score_breakdown 渲染为更强的解释型摘要
