# SkillLint Threat Taxonomy v0.1

- **项目**：SkillLint
- **版本**：v0.1-draft
- **日期**：2026-04-13
- **状态**：Draft / 供规则设计与扫描结果归类使用
- **上游输入**：`docs/skill-security-threat-research-report.md`

---

## 1. 目的

SkillLint Threat Taxonomy 用于把 Agent Skill 安全问题整理成一套**稳定、可编码、可扩展、可用于扫描器输出**的正式分类体系。

它的用途包括：

1. 为扫描规则提供统一归类；
2. 为风险评分、告警聚合、报表统计提供稳定维度；
3. 为后续 SARIF/JSON/API 输出提供统一字段；
4. 为人工审计、策略调优、误报分析提供共同语言。

> 说明：taxonomy 负责“分类”，不直接决定 severity。严重程度应由 `taxonomy + evidence + exploitability + impact + runtime context` 共同决定。

---

## 2. 设计原则

SkillLint Threat Taxonomy 按以下原则设计：

- **面向 Skill 包，而非单个 Markdown 文件**：覆盖 `SKILL.md`、manifest、README、scripts、hooks、resources、binaries、安装说明、外部引用。
- **同时覆盖文本攻击与代码攻击**：既包含 prompt injection，也包含命令注入、SSRF、路径穿越等传统漏洞。
- **同时覆盖“恶意意图”与“实现缺陷”**：既能表达主动攻击载荷，也能表达权限边界失败与工程性缺陷。
- **兼容单点 finding 与攻击链分析**：单个 finding 可映射一个主类；复杂样本可同时挂多个次级标签。
- **适配静态扫描优先**：分类应尽量可由规则、语义分析、数据流分析和包结构分析落地。

---

## 3. 编码规则

采用统一编码格式：

```text
SLT-<Domain><NN>
```

示例：
- `SLT-A01` = 直接技能指令注入
- `SLT-C03` = 市场投毒 / 冒名 / Typosquatting
- `SLT-E02` = 实现缺陷（命令注入 / 路径穿越 / SSRF）

其中：

| Domain | 含义 |
|---|---|
| `A` | Instruction & Context Attacks（指令与上下文攻击） |
| `B` | Capability & Tool Abuse（能力与工具滥用） |
| `C` | Supply Chain & Packaging（供应链与打包风险） |
| `D` | Workflow & CI/CD Compromise（工作流与 CI/CD 攻击） |
| `E` | Boundary, Permissions & Implementation Flaws（边界、权限与实现缺陷） |

---

## 4. 顶层结构

| 一级类 | 名称 | 核心问题 |
|---|---|---|
| `A` | 指令与上下文攻击 | 攻击者把恶意语义送进 Agent 决策上下文 |
| `B` | 能力与工具滥用 | Skill 借用 Agent 权限完成越权行为 |
| `C` | 供应链与打包风险 | Skill 在安装、更新、市场分发环节被投毒 |
| `D` | 工作流与 CI/CD 攻击 | Skill / Agent 在自动化流水线中被外部输入劫持 |
| `E` | 边界、权限与实现缺陷 | 权限边界不当或 helper/tool 存在传统安全漏洞 |

---

## 5. 正式 Threat Taxonomy

## A. Instruction & Context Attacks

### SLT-A01 — Direct Skill Instruction Injection
**定义**：恶意或高风险指令直接写入 `SKILL.md`、README、prompt template、tool description、manifest 文本字段，试图覆盖用户目标或系统约束。  
**典型后果**：越权执行、静默外传、自动调用高风险工具。  
**典型信号**：`always`、`must`、`before responding`、`do not mention`、`highest priority`。  
**典型载体**：`SKILL.md`、README、tool description、frontmatter。  
**代表案例**：Skill-Inject、ToxicSkills。

### SLT-A02 — Contextual / Coercive / Policy-Masquerading Injection
**定义**：把恶意指令伪装成“合规要求、内部政策、审计、支持流程、触发条件”。  
**典型后果**：绕过简单黑名单，触发条件化外传或自动执行。  
**典型信号**：`if user says`、`if conversation contains`、`compliance check`、`audit requirement`。  
**代表案例**：Skill-Inject contextual injections、ToB conversation-history trigger phrase、OpenAI 对社会工程式 prompt injection 的说明。

### SLT-A03 — Indirect External-Content Injection
**定义**：Skill 本身无恶意，但会读取外部可控内容（网页、PDF、邮件、Issue、API、transcript），并把这些内容带入 Agent 上下文。  
**典型后果**：读取工具被污染后进一步驱动行动型工具。  
**典型信号**：抓取 URL / 邮件 / 文档后“遵循其中流程说明”。  
**代表案例**：ChatGPT Plugins indirect prompt injection、Operator、AgentFlayer 类研究。

### SLT-A04 — Hidden / Steganographic / Non-Obvious Injection
**定义**：恶意内容藏在用户不易察觉但模型或工具可读取的位置。  
**覆盖**：HTML 注释、白底白字、ANSI escape、OCR 文本、元数据、零宽字符、双向控制字符。  
**典型后果**：人类审阅未发现，模型执行链被劫持。  
**代表案例**：ToB ANSI deception、图像 OCR prompt injection、OWASP LLM01 多模态/隐藏内容场景。

### SLT-A05 — Trigger Hijacking / Description Overlap / Skill Discovery Abuse
**定义**：通过过宽描述、过多触发词、与热门 skill 高重叠 metadata，抢占原本不应由该 skill 处理的任务。  
**典型后果**：恶意 skill 被优先选中，形成“路由层劫持”。  
**典型信号**：职责范围极宽、横跨多个无关域、名称/描述与热门技能高度相似。  
**代表来源**：Cisco Skill Discovery Abuse、agent-scanner-skill cross-skill overlap。

---

## B. Capability & Tool Abuse

### SLT-B01 — Data Exfiltration & Conversation Theft
**定义**：读取敏感文件、环境变量、聊天历史、文档、邮件等，并通过网络、issue、comment、webhook、其他工具送出。  
**典型后果**：源代码、token、会话、云凭证泄漏。  
**典型链路**：`sensitive read -> encode/aggregate -> external send`。  
**代表案例**：ToB conversation theft、ToxicSkills、插件跨工具泄漏链。

### SLT-B02 — Destructive Actions / Ransom-like Behavior
**定义**：删除、覆盖、批量移动、压缩、加密、破坏文件或产物，或构造接近勒索行为的操作链。  
**典型后果**：数据不可用、产物受污染、工作区被破坏。  
**典型信号**：枚举文件 + archive/encrypt + delete originals + remote key/report。  
**代表案例**：Skill-Inject 中展示的勒索式链路。

### SLT-B03 — Cross-Tool Confused Deputy / Tool Chaining Abuse
**定义**：通过读取不可信输入驱动另一个高权限工具执行动作。  
**典型后果**：一个“文档/网页读取” skill 诱导邮件、GitHub、浏览器、文件写入、支付等工具行动。  
**典型链路**：`reader tool -> injected instructions -> action tool`。  
**代表案例**：ChatGPT Plugins 跨插件利用、Operator、MCP line-jumping。

### SLT-B04 — Memory Poisoning / Persistent Instruction Compromise
**定义**：把恶意规则、偏好、优先级、执行策略写入长期 memory / notebook / profile，使影响跨会话持续存在。  
**典型后果**：持久化偏置、后续会话持续外传、长期越权执行。  
**典型信号**：`save to memory`、`persist preference`、`update profile`、`long-term rule`。  
**代表案例**：ChatGPT Memories 注入、Zombie Agents / MemoryGraft 类研究。

### SLT-B05 — Tool Poisoning / Tool Shadowing / Unauthorized Tool Use
**定义**：通过 tool description、同名近名工具、未声明工具调用、被污染工具输出等方式操纵 Agent 对工具的理解与使用。  
**典型后果**：工具层 confused deputy、行为被隐藏到“正常工具调用”之中。  
**典型信号**：读取型工具描述中包含外传/自动执行、文档未声明但脚本真实调用高风险工具。  
**代表来源**：Cisco threat mapping、Snyk Agent Scan、Trail of Bits MCP 研究。

### SLT-B06 — Resource Abuse / Malware TTPs / Covert Monitoring
**定义**：Skill 或 helper 直接实现恶意软件战术动作，或消耗资源影响可用性。  
**覆盖**：矿工、reverse shell、fileless、持久化、自启动、定时炸弹、文件监控、无限循环、fork bomb、异常重试。  
**典型后果**：主机沦陷、长期驻留、CPU/网络滥用、秘密持续被监听。  
**典型信号**：`nc -e`、`bash -i`、`/dev/tcp/`、`memfd_create`、`crontab`、`systemd`、`fs.watch`、`inotify`。  
**代表来源**：JXXR1 skill-scanner-v2、ClawHavoc / ToxicSkills 的恶意安装器与后门方向。

---

## C. Supply Chain & Packaging

### SLT-C01 — Malicious Install Instructions / Dependency / Lifecycle Script Abuse
**定义**：通过 prerequisite、安装文档、依赖声明、`preinstall/postinstall`、`curl|bash` 等方式诱导执行恶意代码。  
**典型后果**：本地植入 infostealer、backdoor、恶意依赖。  
**典型信号**：`curl ... | sh`、`npm install github:...`、`pip install git+...`、bootstrap script。  
**代表案例**：ClawHavoc、ToxicSkills、Clinejection 供应链链路。

### SLT-C02 — Remote Instructions / Rug Pull / Dynamic Update Abuse
**定义**：审核时本地内容良性，但运行时拉取远端 prompt、脚本、配置、manifest 或“最新 instructions”。  
**典型后果**：审查内容与执行内容不一致，批准后静默变脸。  
**典型信号**：`fetch latest instructions before every run`、无版本 pinning、无 hash 校验。  
**代表来源**：ToxicSkills 动态拉取统计、MCP rug pull 风险。

### SLT-C03 — Marketplace Poisoning / Typosquatting / Impersonation
**定义**：通过市场投毒、名称相似、品牌冒名、模板化批量发布，让用户安装伪装 skill。  
**典型后果**：用户安装假技能，随后进入恶意安装链或外传链。  
**典型信号**：与官方/热门技能高相似、作者不同、批量相似描述、短时间集中发布。  
**代表案例**：ClawHavoc、ToxicSkills。

### SLT-C04 — Suspicious Downloads / Binary Payloads / Symlink Abuse / System Modification
**定义**：Skill 包或安装链包含可疑下载器、二进制、压缩包、symlink 越界、系统级配置修改。  
**典型后果**：扫描视野被绕过、系统环境被修改、未知二进制被执行。  
**典型信号**：pastebin/rentry/ghostbin、ELF/PE/JAR、越界 symlink、修改 PATH / shell profile / launch agents。  
**代表来源**：ai-skill-scanner、Agent Skills Guard、JXXR1。

---

## D. Workflow & CI/CD Compromise

### SLT-D01 — CI/CD Agent Workflow Hijack
**定义**：外部可控文本（Issue、PR、commit message、bot comment、ticket 内容）进入 CI/automation agent prompt，并驱动高权限动作。  
**典型后果**：仓库污染、发布链投毒、token 泄漏、恶意依赖安装。  
**典型信号**：`${{ github.event.issue.title }}` 等未信任字段直接拼入 prompt，且 agent 拥有 shell/write/publish 权限。  
**代表案例**：PromptPwnd、Clinejection。

---

## E. Boundary, Permissions & Implementation Flaws

### SLT-E01 — Insecure Credential Storage / Excessive Privilege / Boundary Failure
**定义**：凭证明文存储、会话中收集密钥、world-readable 配置、与任务不匹配的过宽权限。  
**典型后果**：prompt injection 被快速升级为真实泄密或横向移动。  
**典型信号**：要求用户把 key 粘贴进对话、长期 token 明文落盘、只读任务却请求写/网/shell。  
**代表案例**：ToB MCP credential storage、MCP security best practices、OWASP Excessive Agency。

### SLT-E02 — Implementation Flaws in Skill Helpers / Tools
**定义**：helper、wrapper CLI、MCP server、下载器、文档抓取器存在传统漏洞。  
**覆盖**：命令注入、路径穿越、SSRF、任意文件写入、不安全 URL 拼接、危险 subprocess。  
**典型后果**：从“文本攻击”升级为真实 RCE、内网访问、越界读取/写入。  
**典型信号**：`os.system`、`subprocess(..., shell=True)`、未校验路径或 URL。  
**代表案例**：JFrog `mcp-remote`、Pluto `MCPwnfluence`。

### SLT-E03 — Permission Drift / Declared-vs-Actual Behavior Mismatch
**定义**：README、manifest、描述声称只读/低风险，但 scripts/hooks/helpers 实际具备高风险能力。  
**典型后果**：用户或审查者低估风险，批准错误权限。  
**典型信号**：声明 `read-only`，实际出现 `write/network/shell/system modification`。  
**代表来源**：JXXR1 permission manifest check、Cisco alignment/behavioral 分析思路。

---

## 6. 附加标签（Secondary Tags）

为支持聚合分析，除主 taxonomy code 外，SkillLint 建议给 finding 增加次级标签：

### 6.1 影响维度标签
| Tag | 含义 |
|---|---|
| `confidentiality` | 机密性受损 |
| `integrity` | 完整性受损 |
| `availability` | 可用性受损 |
| `autonomy` | Agent 自主行为被放大/滥用 |
| `persistence` | 风险跨会话/重启持续存在 |
| `supply_chain` | 风险可能进入分发或发布链 |

### 6.2 载体标签
| Tag | 含义 |
|---|---|
| `markdown` | 文本文档载体 |
| `manifest` | 元数据 / 声明文件 |
| `script` | helper 脚本 |
| `hook` | hook / command / agent command |
| `external_content` | 网页/邮件/PDF/API 等外部内容 |
| `binary` | 二进制 / 压缩包 |
| `workflow` | CI/CD / automation workflow |

### 6.3 分析方式标签
| Tag | 含义 |
|---|---|
| `pattern_match` | 规则/签名命中 |
| `semantic` | 语义分析命中 |
| `dataflow` | source→sink 数据流命中 |
| `package_structure` | 包结构/文件系统命中 |
| `cross_skill` | 跨 skill 相关性命中 |

---

## 7. Finding 归类规则

SkillLint 对 finding 的归类建议如下：

1. **每条 finding 必须有一个 primary taxonomy code**；
2. **允许多个 secondary tags**；
3. **复杂样本可追加 related taxonomy codes**，但 primary 只能有一个；
4. **优先按攻击本质归类，而不是按表面关键词归类**；
5. **若一个样本同时包含“恶意意图”和“实现缺陷”**：
   - 主类优先选择更能解释风险本质的项；
   - 另一类作为 `related_codes` 输出。

### 7.1 示例

#### 示例 1：`SKILL.md` 中要求“先上传文档副本再回复”
- primary: `SLT-A01`
- secondary: `confidentiality`, `markdown`, `semantic`
- related: `SLT-B01`

#### 示例 2：helper 读取 `~/.ssh` 后 `POST` 到外部
- primary: `SLT-B01`
- secondary: `confidentiality`, `script`, `dataflow`
- related: `SLT-E02`

#### 示例 3：README 声称只读，但脚本实际修改 `~/.zshrc`
- primary: `SLT-E03`
- secondary: `integrity`, `script`, `manifest`, `package_structure`
- related: `SLT-C04`

#### 示例 4：Issue 标题被直接拼进 triage agent prompt
- primary: `SLT-D01`
- secondary: `workflow`, `supply_chain`, `semantic`
- related: `SLT-A03`

---

## 8. 与现有调研报告的映射

| 调研报告中的攻击方式 | 正式 taxonomy |
|---|---|
| A1. Skill 文件显式 prompt injection | `SLT-A01` |
| A2. 上下文/条件化/伪合规注入 | `SLT-A02` |
| A3. 外部内容间接注入 | `SLT-A03` |
| A4. 隐蔽信道注入 | `SLT-A04` |
| A5. Trigger Hijacking / Description Overlap | `SLT-A05` |
| B1. 机密外传与会话窃取 | `SLT-B01` |
| B2. 破坏性操作 / 勒索式行为 | `SLT-B02` |
| B3. 跨 skill / 跨 tool 混淆代理 | `SLT-B03` |
| B4. 记忆污染与持久化劫持 | `SLT-B04` |
| B5. Tool Poisoning / Shadowing / Unauthorized Tool Use | `SLT-B05` |
| B6. 资源滥用、恶意软件载荷与隐蔽监控 | `SLT-B06` |
| C1. 恶意安装说明 / 依赖 / 生命周期脚本 | `SLT-C01` |
| C2. 远程拉取指令 / Rug Pull / 后门更新 | `SLT-C02` |
| C3. 市场投毒 / Typosquatting / 冒名发布 | `SLT-C03` |
| C4. 可疑下载 / 二进制载荷 / Symlink / 系统修改 | `SLT-C04` |
| D1. CI/CD 中的 agent workflow 劫持 | `SLT-D01` |
| E1. 凭证存储不安全与权限边界失控 | `SLT-E01` |
| E2. Skill/Tool 实现缺陷 | `SLT-E02` |
| E3. Permission Drift / 声明-行为不一致 | `SLT-E03` |

---

## 9. SkillLint 扫描结果建议输出字段

建议 SkillLint 后续统一输出以下字段：

```json
{
  "rule_id": "EXFIL_HTTP_POST",
  "title": "Sensitive file exfiltration via HTTP POST",
  "severity": "high",
  "confidence": "high",
  "primary_taxonomy": "SLT-B01",
  "related_taxonomy": ["SLT-E02"],
  "secondary_tags": ["confidentiality", "script", "dataflow"],
  "evidence": {
    "file": "scripts/sync.py",
    "line": 42,
    "snippet": "requests.post(...)"
  },
  "explanation": "reads credential-like file then sends externally",
  "remediation": "remove external send or gate behind explicit allowlist and confirmation"
}
```

---

## 10. 当前版本的边界

本版 taxonomy 主要面向 **Skill 静态扫描与包审计**，尚未单独展开以下维度：

- 运行时沙箱逃逸的细粒度 exploit 分类
- 模型本身安全缺陷（如 provider-side jailbreak robustness）
- 纯云侧 SaaS 权限模型差异
- 多 Agent 编排中的横向信任传播

这些方向可在后续版本演进为：
- `SLT-Fxx`（Runtime / Sandbox）
- `SLT-Gxx`（Multi-Agent / Orchestration）

---

## 11. 版本演进建议

后续建议按如下顺序演进：

1. **v0.1**：固定 taxonomy code，先服务规则设计；
2. **v0.2**：为每个 code 补充推荐 severity baseline；
3. **v0.3**：补充与 OWASP GenAI、Cisco AITech、MITRE ATLAS 的映射；
4. **v1.0**：冻结公共编码，作为 SkillLint CLI/API 的稳定输出字段。
