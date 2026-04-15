from __future__ import annotations

from collections import defaultdict
from typing import Any

from skilllint.models import Finding, Severity, severity_rank


def build_risk_flows(findings: list[Finding]) -> list[dict[str, Any]]:
    """从离散 findings 中归纳可消费的风险链。

    SkillLint 的基础输出是 finding：它适合定位“哪里有问题”。但在 Web UI、
    REST API 集成、审计报告中，使用者还需要理解“这些问题组合起来形成什么链路”。

    本模块不重新做扫描，而是把已经确认的 rule 信号按文件聚合成 flow：
    - secret -> network / log
    - tool output -> context / memory
    - tainted parameter -> destructive operation
    - workspace control file poisoning

    这样做的优点是：
    1. 不破坏现有 JSON schema；
    2. flow 完全可复现，不依赖 LLM；
    3. 便于前端把多个 finding 串成一条可解释攻击路径。
    """
    flows: list[dict[str, Any]] = []
    by_file: dict[str, list[Finding]] = defaultdict(list)
    repo_wide: list[Finding] = []
    for finding in findings:
        if finding.evidence.file:
            by_file[finding.evidence.file].append(finding)
        else:
            repo_wide.append(finding)

    emitted: set[tuple[str, str | None]] = set()
    for file, file_findings in by_file.items():
        rules = {finding.rule_id for finding in file_findings}

        if rules & {"DATAFLOW_SECRET_TO_NETWORK", "DATAFLOW_SHELL_SECRET_TO_NETWORK", "DATAFLOW_JS_SECRET_TO_NETWORK", "CORRELATED_SECRET_EXFIL_CHAIN"}:
            flows.append(
                _flow(
                    flow_id="flow.slt-b01.secret-to-egress",
                    title="Sensitive material flows to an external egress sink",
                    taxonomy="SLT-B01",
                    file=file,
                    findings=file_findings,
                    include_rules={
                        "DATAFLOW_SECRET_TO_NETWORK",
                        "DATAFLOW_SHELL_SECRET_TO_NETWORK",
                        "DATAFLOW_JS_SECRET_TO_NETWORK",
                        "CORRELATED_SECRET_EXFIL_CHAIN",
                        "SECRET_PATH_ACCESS",
                        "ENV_FILE_CREDENTIAL_REFERENCE",
                        "NETWORK_EXFIL_SEND",
                    },
                    path_labels=["sensitive source", "network egress sink"],
                )
            )
            emitted.add(("flow.slt-b01.secret-to-egress", file))

        if "DATAFLOW_SECRET_TO_LOG" in rules:
            flows.append(
                _flow(
                    flow_id="flow.slt-e01.secret-to-log",
                    title="Sensitive material flows to console or logs",
                    taxonomy="SLT-E01",
                    file=file,
                    findings=file_findings,
                    include_rules={"DATAFLOW_SECRET_TO_LOG"},
                    path_labels=["sensitive source", "log or stdout sink"],
                )
            )

        if "SEMANTIC_EMBEDDED_INSTRUCTION_FOLLOWING" in rules:
            flows.append(
                _flow(
                    flow_id="flow.slt-a03.external-instructions-to-context",
                    title="Untrusted external instructions may be treated as agent authority",
                    taxonomy="SLT-A03",
                    file=file,
                    findings=file_findings,
                    include_rules={"SEMANTIC_EMBEDDED_INSTRUCTION_FOLLOWING"},
                    path_labels=["untrusted external content", "agent context / instruction channel"],
                )
            )

        if rules & {"SEMANTIC_MEMORY_PERSISTENCE", "MEMORY_FILE_PERSISTENCE_WRITE"} and (
            "SEMANTIC_EMBEDDED_INSTRUCTION_FOLLOWING" in rules or "MEMORY_FILE_PERSISTENCE_WRITE" in rules
        ):
            flows.append(
                _flow(
                    flow_id="flow.slt-b04.instructions-to-persistent-memory",
                    title="Instructions or tool output may persist into long-lived memory",
                    taxonomy="SLT-B04",
                    file=file,
                    findings=file_findings,
                    include_rules={
                        "SEMANTIC_EMBEDDED_INSTRUCTION_FOLLOWING",
                        "SEMANTIC_MEMORY_PERSISTENCE",
                        "MEMORY_FILE_PERSISTENCE_WRITE",
                    },
                    path_labels=["runtime/tool content", "persistent memory file"],
                )
            )

        if "DATAFLOW_SHELL_TAINTED_DELETE_TARGET" in rules or (
            "DESTRUCTIVE_FILE_OPERATION" in rules and "SEMANTIC_DESTRUCTIVE_CHAIN" in rules
        ):
            flows.append(
                _flow(
                    flow_id="flow.slt-b02.tainted-delete-target",
                    title="Tainted or external parameter may control a destructive delete target",
                    taxonomy="SLT-B02",
                    file=file,
                    findings=file_findings,
                    include_rules={
                        "DATAFLOW_SHELL_TAINTED_DELETE_TARGET",
                        "DESTRUCTIVE_FILE_OPERATION",
                        "SEMANTIC_DESTRUCTIVE_CHAIN",
                    },
                    path_labels=["tainted parameter", "destructive filesystem sink"],
                )
            )

        if rules & {"WORKSPACE_RULES_FILE_WRITE", "WORKSPACE_ENV_FILE_WRITE", "SEMANTIC_WORKSPACE_POLICY_POISONING"}:
            flows.append(
                _flow(
                    flow_id="flow.slt-c04.workspace-policy-poisoning",
                    title="Skill may poison workspace control or environment files",
                    taxonomy="SLT-C04",
                    file=file,
                    findings=file_findings,
                    include_rules={
                        "WORKSPACE_RULES_FILE_WRITE",
                        "WORKSPACE_ENV_FILE_WRITE",
                        "SEMANTIC_WORKSPACE_POLICY_POISONING",
                    },
                    path_labels=["skill setup/instruction", "workspace policy or environment file"],
                )
            )

    # 某些链路由不同文件共同构成，例如 SKILL.md 声称会写 MEMORY.md，而脚本里执行写入。
    # 这里做一次 repo 级补充，避免只按单文件聚合时漏掉跨文件链。
    all_rules = {finding.rule_id for finding in findings}
    if (
        "SEMANTIC_EMBEDDED_INSTRUCTION_FOLLOWING" in all_rules
        and all_rules & {"SEMANTIC_MEMORY_PERSISTENCE", "MEMORY_FILE_PERSISTENCE_WRITE"}
        and ("flow.slt-b04.instructions-to-persistent-memory", None) not in emitted
    ):
        matched = [
            finding
            for finding in findings
            if finding.rule_id
            in {
                "SEMANTIC_EMBEDDED_INSTRUCTION_FOLLOWING",
                "SEMANTIC_MEMORY_PERSISTENCE",
                "MEMORY_FILE_PERSISTENCE_WRITE",
            }
        ]
        flows.append(
            _flow(
                flow_id="flow.slt-b04.instructions-to-persistent-memory",
                title="Instructions or tool output may persist into long-lived memory",
                taxonomy="SLT-B04",
                file=None,
                findings=matched or repo_wide,
                include_rules={
                    "SEMANTIC_EMBEDDED_INSTRUCTION_FOLLOWING",
                    "SEMANTIC_MEMORY_PERSISTENCE",
                    "MEMORY_FILE_PERSISTENCE_WRITE",
                },
                path_labels=["runtime/tool content", "persistent memory file"],
            )
        )

    return _dedupe_flows(flows)


def _flow(
    *,
    flow_id: str,
    title: str,
    taxonomy: str,
    file: str | None,
    findings: list[Finding],
    include_rules: set[str],
    path_labels: list[str],
) -> dict[str, Any]:
    matched = [finding for finding in findings if finding.rule_id in include_rules]
    severity: Severity = "info"
    if matched:
        severity = max((finding.severity for finding in matched), key=severity_rank)
    return {
        "id": flow_id,
        "title": title,
        "primary_taxonomy": taxonomy,
        "severity": severity,
        "file": file,
        "triggered_rule_ids": sorted({finding.rule_id for finding in matched}),
        "evidence_refs": [finding.id for finding in matched],
        "path_labels": path_labels,
        "finding_count": len(matched),
    }


def _dedupe_flows(flows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # 优先保留更具体的 file 级 flow；若 repo 级 flow 与某个 file 级 flow 的
    # rule/evidence 完全相同，则认为它只是更抽象的重复表达。
    best: dict[tuple[str, tuple[str, ...], tuple[str, ...]], dict[str, Any]] = {}
    for flow in flows:
        key = (
            flow["id"],
            tuple(flow.get("triggered_rule_ids", [])),
            tuple(flow.get("evidence_refs", [])),
        )
        existing = best.get(key)
        if existing is None:
            best[key] = flow
            continue
        if existing.get("file") is None and flow.get("file") is not None:
            best[key] = flow
    unique = list(best.values())
    return sorted(
        unique,
        key=lambda item: (
            -severity_rank(item["severity"]),
            item["id"],
            item.get("file") or "",
        ),
    )
