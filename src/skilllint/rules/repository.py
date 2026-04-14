from __future__ import annotations

import re
from fnmatch import fnmatch
from functools import lru_cache
from importlib import resources
from typing import Any
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field

from skilllint.models import Confidence, Evidence, Finding, Severity


class RuleMeta(BaseModel):
    rule_id: str
    title: str
    severity: Severity
    taxonomy: str
    tags: list[str] = Field(default_factory=list)
    explanation: str = ""
    remediation: str = ""
    confidence: Confidence = "medium"
    metadata: dict[str, Any] = Field(default_factory=dict)
    path_include_globs: list[str] = Field(default_factory=list)
    path_exclude_globs: list[str] = Field(default_factory=list)
    max_matches_per_file: int | None = None

    def applies_to_path(self, rel_path: str | None) -> bool:
        if rel_path is None:
            return True
        normalized = rel_path.replace("\\", "/")
        if self.path_include_globs and not any(fnmatch(normalized, pattern) for pattern in self.path_include_globs):
            return False
        if self.path_exclude_globs and any(fnmatch(normalized, pattern) for pattern in self.path_exclude_globs):
            return False
        return True


class RegexRule(RuleMeta):
    pattern: str
    flags: list[str] = Field(default_factory=lambda: ["IGNORECASE"])

    @property
    def compiled_flags(self) -> int:
        combined = 0
        for flag_name in self.flags:
            combined |= getattr(re, flag_name.upper(), 0)
        return combined


class StaticRuleCatalog(BaseModel):
    rules: list[RuleMeta]


class SemanticRule(RuleMeta):
    all_of_groups: list[str] = Field(default_factory=list)
    any_of_groups: list[str] = Field(default_factory=list)
    hint_group: str | None = None


class SemanticCatalog(BaseModel):
    keyword_groups: dict[str, list[str]] = Field(default_factory=dict)
    rules: list[SemanticRule] = Field(default_factory=list)


class RuleRepository:
    def __init__(self) -> None:
        self._regex_catalog = _load_yaml_resource("skilllint.rules.regex", "rules.yaml", list[RegexRule])
        self._package_catalog = _load_yaml_resource(
            "skilllint.rules.package", "rules.yaml", StaticRuleCatalog
        )
        self._semantic_catalog = _load_yaml_resource(
            "skilllint.rules.semantic", "rules.yaml", SemanticCatalog
        )
        self._dataflow_catalog = _load_yaml_resource(
            "skilllint.rules.dataflow", "rules.yaml", StaticRuleCatalog
        )

        self._package_rules = {rule.rule_id: rule for rule in self._package_catalog.rules}
        self._dataflow_rules = {rule.rule_id: rule for rule in self._dataflow_catalog.rules}

    @property
    def regex_rules(self) -> list[RegexRule]:
        return list(self._regex_catalog)

    @property
    def semantic_keyword_groups(self) -> dict[str, list[str]]:
        return dict(self._semantic_catalog.keyword_groups)

    @property
    def semantic_rules(self) -> list[SemanticRule]:
        return list(self._semantic_catalog.rules)

    @property
    def package_rules(self) -> list[RuleMeta]:
        return list(self._package_catalog.rules)

    @property
    def dataflow_rules(self) -> list[RuleMeta]:
        return list(self._dataflow_catalog.rules)

    def package_rule(self, rule_id: str) -> RuleMeta:
        return self._package_rules[rule_id]

    def dataflow_rule(self, rule_id: str) -> RuleMeta:
        return self._dataflow_rules[rule_id]


@lru_cache(maxsize=1)
def get_rule_repository() -> RuleRepository:
    return RuleRepository()


def build_finding(
    *,
    rule: RuleMeta,
    engine: str,
    evidence: Evidence | None = None,
    related_taxonomy: list[str] | None = None,
    metadata: dict[str, Any] | None = None,
) -> Finding:
    combined_metadata = dict(rule.metadata)
    if metadata:
        combined_metadata.update(metadata)
    return Finding(
        id=str(uuid4()),
        rule_id=rule.rule_id,
        title=rule.title,
        severity=rule.severity,
        confidence=rule.confidence,
        engine=engine,
        primary_taxonomy=rule.taxonomy,
        related_taxonomy=related_taxonomy or [],
        secondary_tags=list(rule.tags),
        explanation=rule.explanation,
        remediation=rule.remediation,
        evidence=evidence or Evidence(),
        metadata=combined_metadata,
    )


def _load_yaml_resource(package: str, name: str, model: Any) -> Any:
    resource = resources.files(package).joinpath(name)
    with resource.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    if getattr(model, "__origin__", None) is list:
        item_model = model.__args__[0]
        return [item_model.model_validate(item) for item in data]
    return model.model_validate(data)
