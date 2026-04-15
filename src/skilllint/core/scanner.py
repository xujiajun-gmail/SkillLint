from __future__ import annotations

from skilllint import __version__
from skilllint.config import SkillLintConfig
from skilllint.core.workspace import PreparedWorkspace, cleanup_workspace, prepare_workspace
from skilllint.engines.dataflow_engine import DataflowEngine
from skilllint.engines.package_engine import PackageEngine
from skilllint.engines.regex_engine import RegexEngine
from skilllint.engines.semantic_engine import SemanticEngine
from skilllint.flows import build_risk_flows
from skilllint.models import Finding, ScanResult, TargetInfo
from skilllint.rules.repository import get_rule_repository
from skilllint.rules.selector import RuleSelector
from skilllint.scoring import build_score_breakdown, build_summary, correlate_findings
from skilllint.taxonomy.mapper import map_finding_taxonomy
from skilllint.utils.language import detect_language_from_paths, dominant_source_language


class SkillScanner:
    def __init__(self, config: SkillLintConfig) -> None:
        self.config = config
        # 规则过滤器在扫描入口统一构造，后续各引擎共享同一份裁剪视图。
        self.rule_selector = RuleSelector(
            include_rule_ids=set(config.rules.include_rule_ids),
            exclude_rule_ids=set(config.rules.exclude_rule_ids),
            include_taxonomies=set(config.rules.include_taxonomies),
            exclude_taxonomies=set(config.rules.exclude_taxonomies),
        )

    def scan(self, target: TargetInfo) -> ScanResult:
        """执行一次完整扫描。

        主流程：
        1. 准备统一工作区
        2. 依次运行各检测引擎
        3. 做 taxonomy 映射与 finding correlation
        4. 计算 summary / score breakdown
        5. 产出统一 ScanResult
        """
        workspace = prepare_workspace(target, self.config)
        try:
            findings, engine_meta = self._run_engines(workspace)
            # 部分引擎会直接给出 taxonomy，部分只给 rule_id，因此在这里统一补齐。
            findings = [map_finding_taxonomy(f) for f in findings]
            # correlation 是“第二层信号”：它不替代引擎 finding，而是放大组合风险。
            correlation_outcome = correlate_findings(findings)
            findings = correlation_outcome.findings
            findings.sort(key=self._sort_key, reverse=True)
            language = self._resolve_language(workspace)
            summary = build_summary(findings, correlation_outcome.hits)
            score_breakdown = build_score_breakdown(findings, correlation_outcome.hits)
            # risk_flows 是对离散 findings 的链路化解释，便于 API/UI 展示“源 -> 汇”的攻击路径。
            risk_flows = build_risk_flows(findings)
            repository = get_rule_repository()
            return ScanResult(
                scan_id=workspace.scan_id,
                tool_version=__version__,
                target=target,
                workspace=workspace.to_model(),
                language=language,
                summary=summary,
                findings=findings,
                metadata={
                    "profile": self.config.profile,
                    "source_language": dominant_source_language(workspace.all_files()),
                    "enabled_engines": self._enabled_engine_names(),
                    "rule_catalog": {
                        "regex": len(repository.regex_rules),
                        "package": len(repository.package_rules),
                        "semantic": len(repository.semantic_rules),
                        "dataflow": len(repository.dataflow_rules),
                    },
                    "rule_filters": self.rule_selector.to_metadata(),
                    "correlation_hits": [
                        hit.model_dump() for hit in correlation_outcome.hits
                    ],
                    "risk_flows": risk_flows,
                    "score_breakdown": score_breakdown,
                    **engine_meta,
                },
            )
        finally:
            cleanup_workspace(workspace, self.config.workspace.keep_artifacts)

    def _run_engines(self, workspace: PreparedWorkspace) -> tuple[list[Finding], dict[str, str]]:
        # 这里使用固定顺序执行引擎，便于：
        # 1) 行为可预测；2) semantic 能利用前序 finding 作为 seed；3) 输出更稳定。
        findings: list[Finding] = []
        engine_meta: dict[str, str] = {}
        if self.config.engines.package.enabled:
            findings.extend(PackageEngine(self.rule_selector).run(workspace))
        if self.config.engines.regex.enabled:
            findings.extend(RegexEngine(self.rule_selector).run(workspace))
        if self.config.engines.semantic.enabled:
            semantic_engine = SemanticEngine(self.config, self.rule_selector)
            # semantic engine 会读取前序 findings 作为 seed，用于 permission drift / LLM 候选选择。
            semantic_findings = semantic_engine.run(workspace, findings)
            findings.extend(semantic_findings)
            engine_meta["semantic_llm_status"] = semantic_engine.last_llm_status
            if self.config.llm.debug and semantic_engine.last_llm_debug_records:
                engine_meta["semantic_llm_debug"] = semantic_engine.last_llm_debug_records
        if self.config.engines.dataflow.enabled:
            findings.extend(DataflowEngine(self.rule_selector).run(workspace))
        return findings, engine_meta

    def _resolve_language(self, workspace: PreparedWorkspace) -> str:
        # 若用户显式指定报告语言，则优先使用；否则基于样本内容自动判断。
        report_language = self.config.outputs.report_language
        if report_language in {"zh", "en"}:
            return report_language
        return detect_language_from_paths(workspace.all_files())

    @staticmethod
    def _sort_key(finding: Finding) -> tuple[int, str]:
        order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
        return order[finding.severity], finding.rule_id

    def _enabled_engine_names(self) -> list[str]:
        names = []
        if self.config.engines.package.enabled:
            names.append("package")
        if self.config.engines.regex.enabled:
            names.append("regex")
        if self.config.engines.semantic.enabled:
            names.append("semantic")
        if self.config.engines.dataflow.enabled:
            names.append("dataflow")
        return names
