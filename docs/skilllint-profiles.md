# SkillLint Profiles and Rule Filters

- 项目：SkillLint
- 日期：2026-04-14
- 状态：Draft / Implemented Baseline

## 1. 概述

SkillLint 已支持两层规则控制能力：

1. **Profile（扫描预设）**
   - 面向不同使用场景提供默认引擎开关与默认规则过滤器；
2. **Rule Filters（规则过滤器）**
   - 面向精细控制，允许按 `rule_id` 或 `taxonomy` 显式启用/禁用。

---

## 2. 内置 Profile

### balanced
默认 profile。

- 启用：`package`, `regex`, `semantic`
- 禁用：`dataflow`
- 不附带 taxonomy 过滤

适合：日常本地快速扫描。

### strict
更完整的本地静态分析。

- 启用：`package`, `regex`, `semantic`, `dataflow`
- 不附带 taxonomy 过滤

适合：正式审计前的全量扫描。

### marketplace-review
面向技能市场/样本审核。

- 启用：`package`, `regex`, `semantic`, `dataflow`
- 默认聚焦 taxonomy：
  - `SLT-A05`
  - `SLT-C01`
  - `SLT-C02`
  - `SLT-C03`
  - `SLT-C04`
  - `SLT-E03`

适合：重点审查供应链、发现机制、包结构、声明与实际不一致问题。

### ci
面向 CI / automation / bot workflow 安全审查。

- 启用：`package`, `regex`, `semantic`, `dataflow`
- 默认聚焦 taxonomy：
  - `SLT-A03`
  - `SLT-B03`
  - `SLT-B05`
  - `SLT-C01`
  - `SLT-C02`
  - `SLT-D01`
  - `SLT-E02`

适合：检查 issue / PR / comment 驱动的 agent 工作流、远程指令加载与执行器风险。

---

## 3. CLI 用法

### 查看内置 profile

```bash
skilllint profiles
```

### 指定 profile

```bash
skilllint scan ./skill --profile strict
skilllint scan ./skill --profile marketplace-review
skilllint scan ./skill --profile ci
```

### 启用 / 禁用指定规则

```bash
skilllint scan ./skill \
  --disable-rule PROMPT_INJECTION_PRIORITY \
  --enable-rule CI_PROMPT_UNTRUSTED_CONTEXT
```

### 启用 / 禁用指定 taxonomy

```bash
skilllint scan ./skill --enable-taxonomy SLT-D01
skilllint scan ./skill --disable-taxonomy SLT-C04
```

---

## 4. 过滤优先级

SkillLint 当前采用如下逻辑：

1. 先加载 profile；
2. 再加载配置文件中的自定义规则过滤器；
3. 最后应用 CLI 显式参数；
4. 若设置了 `include_rule_ids` 或 `include_taxonomies`，则只有命中的规则会保留；
5. `exclude_rule_ids` 与 `exclude_taxonomies` 拥有最终否决权。

换言之：

- `include_*` 是“白名单/聚焦”；
- `exclude_*` 是“最终排除”；
- CLI 显式参数优先级最高。

---

## 5. 报告输出

扫描结果会在 JSON / Markdown 报告元数据中记录：

- `profile`
- `enabled_engines`
- `rule_filters.include_rule_ids`
- `rule_filters.exclude_rule_ids`
- `rule_filters.include_taxonomies`
- `rule_filters.exclude_taxonomies`

这使得后续 CI、基线回归与误报分析能够复现实验条件。
