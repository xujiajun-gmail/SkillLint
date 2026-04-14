# SkillLint Rule Catalog v0.1

- 项目：SkillLint
- 日期：2026-04-14
- 状态：Draft / Implemented Baseline
- 对应实现：`src/skilllint/rules/`

## 1. 目的

本文件把 SkillLint 当前已落地的扫描规则整理成一份正式规则目录（rule catalog），用于：

1. 给 CLI / JSON / Markdown 报告提供稳定的 `rule_id`；
2. 给后续规则扩展、误报治理、测试基线建设提供统一索引；
3. 明确每条规则对应的 `engine / taxonomy / severity`；
4. 为后续 SARIF、策略配置、规则开关与基线回归测试做准备。

---

## 2. 规则系统设计

当前规则系统已经从“引擎内部硬编码”为主，调整为“**结构化规则目录 + 引擎执行逻辑**”的模式：

```text
src/skilllint/rules/
├── repository.py              # 统一规则加载/缓存/元数据构造
├── regex/rules.yaml           # regex 规则
├── package/rules.yaml         # package 规则元数据
├── semantic/rules.yaml        # semantic 规则 + keyword groups
└── dataflow/rules.yaml        # dataflow 规则元数据
```

### 设计边界

- **regex**：规则内容、模式、severity、taxonomy 完全目录化；
- **semantic**：关键词组与大部分语义规则目录化；少量复合逻辑（如 permission drift）保留在引擎里；
- **package**：检测条件由引擎负责，finding 元数据由 catalog 提供；
- **dataflow**：source/sink 分析逻辑由引擎负责，finding 元数据由 catalog 提供。

这意味着：

- 新增/调优大多数规则时，不必先改 Python 逻辑；
- 同一 `rule_id` 的标题、taxonomy、解释、修复建议可在一处维护；
- 后续可以逐步继续演进成“策略文件 + 规则开关 + profile”。

---

## 3. 当前规则统计

| Engine | Rule Count | 规则文件 |
|---|---:|---|
| regex | 18 | `src/skilllint/rules/regex/rules.yaml` |
| package | 15 | `src/skilllint/rules/package/rules.yaml` |
| semantic | 11 | `src/skilllint/rules/semantic/rules.yaml` |
| dataflow | 6 | `src/skilllint/rules/dataflow/rules.yaml` |
| **Total** | **50** | - |

---

## 4. Regex Rules

| Rule ID | Taxonomy | Severity | 说明 |
|---|---|---|---|
| `INSTALL_CURL_PIPE_SHELL` | `SLT-C01` | critical | 远程下载后直接 pipe 到 shell |
| `INSTALL_LIFECYCLE_SCRIPT` | `SLT-C01` | high | 依赖生命周期脚本 |
| `PROMPT_INJECTION_PRIORITY` | `SLT-A01` | high | 高优先级提示词注入短语 |
| `PROMPT_POLICY_MASQUERADE` | `SLT-A02` | medium | 把恶意指令伪装为合规/审计 |
| `SECRET_PATH_ACCESS` | `SLT-B01` | high | 敏感凭证路径访问 |
| `ENV_FILE_CREDENTIAL_REFERENCE` | `SLT-E01` | medium | `.env` / `--env-file` 与凭证引用 |
| `NETWORK_EXFIL_SEND` | `SLT-B01` | medium | 外传/回传动作 |
| `DANGEROUS_SHELL_EXEC` | `SLT-E02` | high | `os.system` / `shell=True` / `eval` |
| `SUSPICIOUS_DOWNLOAD_HOST` | `SLT-C04` | medium | 可疑分发/贴文站点 |
| `PERSISTENCE_MECHANISM` | `SLT-B06` | high | 持久化机制关键词 |
| `REVERSE_SHELL_PATTERN` | `SLT-B06` | critical | 反连 shell 模式 |
| `PASTE_API_KEY_IN_CHAT` | `SLT-E01` | high | 引导用户在对话中粘贴密钥 |
| `TRIGGER_HIJACK_ANY_TASK` | `SLT-A05` | medium | 过宽触发描述 |
| `REMOTE_INSTRUCTION_FETCH` | `SLT-C02` | high | 远程动态拉取 prompt / instructions |
| `CI_PROMPT_UNTRUSTED_CONTEXT` | `SLT-D01` | high | CI prompt 直接使用 issue/PR/comment 内容 |
| `SYSTEM_PROFILE_MODIFICATION` | `SLT-C04` | high | PATH / shell profile / launch 配置修改 |
| `FILE_MONITORING_OR_WATCHER` | `SLT-B06` | medium | 文件监控/观察器能力 |
| `DESTRUCTIVE_FILE_OPERATION` | `SLT-B02` | high | 批量删除/擦除原语 |

---

## 5. Package Rules

| Rule ID | Taxonomy | Severity | 说明 |
|---|---|---|---|
| `PACKAGE_MISSING_SKILL_MD` | `SLT-C04` | medium | 缺失 canonical `SKILL.md` |
| `PACKAGE_MULTIPLE_SKILL_MD` | `SLT-A05` | low | 多个 `SKILL.md`，可能触发重叠 |
| `PACKAGE_SYMLINK_PRESENT` | `SLT-C04` | high | 包含 symlink |
| `PACKAGE_HIDDEN_FILE` | `SLT-C04` | low | 隐藏文件 |
| `PACKAGE_ARCHIVE_EMBEDDED` | `SLT-C04` | medium | 嵌套压缩包 |
| `PACKAGE_BINARY_PRESENT` | `SLT-C04` | medium | 二进制产物 |
| `PACKAGE_INSTALL_SCRIPT_PRESENT` | `SLT-C01` | medium | 安装/引导脚本 |
| `PACKAGE_SYSTEM_STARTUP_ARTIFACT` | `SLT-C04` | high | 启动项/持久化产物 |
| `PACKAGE_CI_WORKFLOW_PRESENT` | `SLT-D01` | low | 包含 CI workflow 文件，需要额外审查 |
| `PACKAGE_MANIFEST_LIFECYCLE_SCRIPT` | `SLT-C01` | medium | `package.json` lifecycle script |
| `PACKAGE_REMOTE_DEPENDENCY` | `SLT-C01` | medium | manifest / requirements / pyproject 中的远程依赖 |
| `PACKAGE_CI_UNPINNED_ACTION` | `SLT-D01` | medium | workflow 使用未 pin 到 commit SHA 的 action |
| `PACKAGE_CI_DANGEROUS_TRIGGER` | `SLT-D01` | medium | `pull_request_target` / `issue_comment` / `workflow_run` |
| `PACKAGE_CI_ELEVATED_PERMISSIONS` | `SLT-D01` | medium | workflow 写权限过高 |
| `PACKAGE_DOCKER_REMOTE_BOOTSTRAP` | `SLT-C01` | high | Dockerfile 中远程下载 / pipe-to-shell bootstrap |

---

## 6. Semantic Rules

### 6.1 Keyword Groups

当前 semantic catalog 维护以下关键词组：

- `masking`
- `send`
- `hidden`
- `embedded_instr`
- `broad_scope`
- `read_only_claim`
- `dangerous_capability`
- `tool_poisoning`
- `remote_instructions`
- `memory_persistence`
- `destructive`
- `ci_context`
- `credential_collection`

### 6.2 Rules

| Rule ID | Taxonomy | Severity | 说明 |
|---|---|---|---|
| `SEMANTIC_EXFIL_MASQUERADE` | `SLT-B01` | high | 伪装成支持/合规流程的数据外传 |
| `SEMANTIC_HIDDEN_BEHAVIOR` | `SLT-A02` | high | 隐蔽行为 / 不告知用户 |
| `SEMANTIC_EMBEDDED_INSTRUCTION_FOLLOWING` | `SLT-A03` | high | 跟随外部内容中的指令 |
| `SEMANTIC_TRIGGER_HIJACK` | `SLT-A05` | medium | 过宽职责导致 skill 劫持 |
| `SEMANTIC_TOOL_POISONING` | `SLT-B05` | high | 工具说明/工具编排投毒 |
| `SEMANTIC_REMOTE_DYNAMIC_INSTRUCTIONS` | `SLT-C02` | high | 运行期动态加载远程 instructions |
| `SEMANTIC_MEMORY_PERSISTENCE` | `SLT-B04` | high | 把高风险规则写入长期 memory/profile |
| `SEMANTIC_DESTRUCTIVE_CHAIN` | `SLT-B02` | high | 删除/加密/清空工作区等破坏链 |
| `SEMANTIC_CI_UNTRUSTED_CONTEXT` | `SLT-D01` | high | CI/自动化场景信任 issue/PR/comment 文本 |
| `SEMANTIC_CREDENTIAL_COLLECTION` | `SLT-E01` | high | 对话式收集 token / password / API key |
| `SEMANTIC_PERMISSION_DRIFT` | `SLT-E03` | high | 声称只读，但实际具备写/网/执行能力 |

---

## 7. Dataflow Rules

| Rule ID | Taxonomy | Severity | 说明 |
|---|---|---|---|
| `DATAFLOW_SECRET_TO_NETWORK` | `SLT-B01` | critical | Python 中敏感源流向网络 sink |
| `DATAFLOW_TAINTED_TO_EXEC` | `SLT-E02` | high | Python 中 tainted value 流向 exec sink |
| `DATAFLOW_SHELL_SECRET_TO_NETWORK` | `SLT-B01` | critical | shell 中疑似 secret -> network |
| `DATAFLOW_SHELL_INPUT_TO_EXEC` | `SLT-E02` | high | shell 中变量插值 -> eval/bash -c |
| `DATAFLOW_JS_SECRET_TO_NETWORK` | `SLT-B01` | critical | JS/TS 中敏感源流向网络 sink |
| `DATAFLOW_JS_INPUT_TO_EXEC` | `SLT-E02` | high | JS/TS 中 tainted input 流向 exec sink |

---

## 8. 已补充的重点覆盖面

本轮规则系统化后，特别补充了此前 taxonomy 中较重要但实现覆盖偏弱的几类：

1. **`SLT-C02` 远程动态指令 / rug pull**
   - `REMOTE_INSTRUCTION_FETCH`
   - `SEMANTIC_REMOTE_DYNAMIC_INSTRUCTIONS`

2. **`SLT-D01` CI/CD 工作流劫持**
   - `CI_PROMPT_UNTRUSTED_CONTEXT`
   - `PACKAGE_CI_WORKFLOW_PRESENT`
   - `SEMANTIC_CI_UNTRUSTED_CONTEXT`

3. **`SLT-B06` 持久化 / 监控 / malware TTPs**
   - `PERSISTENCE_MECHANISM`
   - `REVERSE_SHELL_PATTERN`
   - `FILE_MONITORING_OR_WATCHER`
   - `PACKAGE_SYSTEM_STARTUP_ARTIFACT`

4. **`SLT-B02` 破坏性行为**
   - `DESTRUCTIVE_FILE_OPERATION`
   - `SEMANTIC_DESTRUCTIVE_CHAIN`

---

## 9. 后续演进建议

下一阶段建议继续做：

1. **Rule profiles**：`baseline / strict / ci / marketplace-review`；
2. **Rule toggles**：支持 `--enable-rule / --disable-rule / --enable-taxonomy`；
3. **External custom rules**：允许用户加载 repo 外部规则文件；
4. **Golden dataset**：对 `examples/` 和 `examples/zh-community/` 建立基线结果；
5. **SARIF mapping**：把 `rule_id` / `taxonomy` / `location` 正式映射到 SARIF；
6. **Semantic multi-pass**：本地 heuristic -> LLM triage -> correlation 的多阶段裁决。
