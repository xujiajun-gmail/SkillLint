from __future__ import annotations

from collections import Counter

from skilllint import __version__
from skilllint.config import SkillLintConfig
from skilllint.core.workspace import PreparedWorkspace, cleanup_workspace, prepare_workspace
from skilllint.engines.dataflow_engine import DataflowEngine
from skilllint.engines.package_engine import PackageEngine
from skilllint.engines.regex_engine import RegexEngine
from skilllint.engines.semantic_engine import SemanticEngine
from skilllint.models import Finding, ScanResult, ScanSummary, Severity, TargetInfo
from skilllint.rules.repository import get_rule_repository
from skilllint.rules.selector import RuleSelector
from skilllint.taxonomy.mapper import correlate_findings, map_finding_taxonomy
from skilllint.utils.language import detect_language_from_paths, dominant_source_language


class SkillScanner:
    def __init__(self, config: SkillLintConfig) -> None:
        self.config = config
        self.rule_selector = RuleSelector(
            include_rule_ids=set(config.rules.include_rule_ids),
            exclude_rule_ids=set(config.rules.exclude_rule_ids),
            include_taxonomies=set(config.rules.include_taxonomies),
            exclude_taxonomies=set(config.rules.exclude_taxonomies),
        )

    def scan(self, target: TargetInfo) -> ScanResult:
        workspace = prepare_workspace(target, self.config)
        try:
            findings, engine_meta = self._run_engines(workspace)
            findings = [map_finding_taxonomy(f) for f in findings]
            findings = correlate_findings(findings)
            findings.sort(key=self._sort_key, reverse=True)
            language = self._resolve_language(workspace)
            summary = self._build_summary(findings)
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
                    **engine_meta,
                },
            )
        finally:
            cleanup_workspace(workspace, self.config.workspace.keep_artifacts)

    def _run_engines(self, workspace: PreparedWorkspace) -> tuple[list[Finding], dict[str, str]]:
        findings: list[Finding] = []
        engine_meta: dict[str, str] = {}
        if self.config.engines.package.enabled:
            findings.extend(PackageEngine(self.rule_selector).run(workspace))
        if self.config.engines.regex.enabled:
            findings.extend(RegexEngine(self.rule_selector).run(workspace))
        if self.config.engines.semantic.enabled:
            semantic_engine = SemanticEngine(self.config, self.rule_selector)
            semantic_findings = semantic_engine.run(workspace, findings)
            findings.extend(semantic_findings)
            engine_meta["semantic_llm_status"] = semantic_engine.last_llm_status
        if self.config.engines.dataflow.enabled:
            findings.extend(DataflowEngine(self.rule_selector).run(workspace))
        return findings, engine_meta

    def _resolve_language(self, workspace: PreparedWorkspace) -> str:
        report_language = self.config.outputs.report_language
        if report_language in {"zh", "en"}:
            return report_language
        return detect_language_from_paths(workspace.all_files())

    def _build_summary(self, findings: list[Finding]) -> ScanSummary:
        counts = Counter(f.severity for f in findings)
        risk_level = self._max_severity(findings)
        verdict = self._verdict_from_severity(risk_level)
        return ScanSummary(
            risk_level=risk_level,
            verdict=verdict,
            finding_count=len(findings),
            critical=counts.get("critical", 0),
            high=counts.get("high", 0),
            medium=counts.get("medium", 0),
            low=counts.get("low", 0),
            info=counts.get("info", 0),
        )

    @staticmethod
    def _max_severity(findings: list[Finding]) -> Severity:
        order = ["info", "low", "medium", "high", "critical"]
        if not findings:
            return "info"
        return max((f.severity for f in findings), key=lambda s: order.index(s))  # type: ignore[return-value]

    @staticmethod
    def _verdict_from_severity(severity: Severity) -> str:
        if severity == "critical":
            return "malicious"
        if severity == "high":
            return "suspicious"
        if severity == "medium":
            return "needs_review"
        return "safe"

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
