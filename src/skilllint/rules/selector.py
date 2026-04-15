from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RuleSelector:
    """规则/Taxonomy 过滤器。

    设计目标是把“规则裁剪策略”从引擎实现中剥离出去，
    这样 regex/package/semantic/dataflow 都能复用同一套 include/exclude 语义。
    """
    include_rule_ids: set[str] = field(default_factory=set)
    exclude_rule_ids: set[str] = field(default_factory=set)
    include_taxonomies: set[str] = field(default_factory=set)
    exclude_taxonomies: set[str] = field(default_factory=set)

    def allows_rule(self, rule_id: str, taxonomy: str | None = None) -> bool:
        # include 存在时采用白名单语义；否则默认允许，再看 exclude 黑名单。
        included = True
        if self.include_rule_ids or self.include_taxonomies:
            included = rule_id in self.include_rule_ids or (
                taxonomy is not None and taxonomy in self.include_taxonomies
            )
        if not included:
            return False
        if rule_id in self.exclude_rule_ids:
            return False
        if taxonomy is not None and taxonomy in self.exclude_taxonomies:
            return False
        return True

    def to_metadata(self) -> dict[str, list[str]]:
        return {
            "include_rule_ids": sorted(self.include_rule_ids),
            "exclude_rule_ids": sorted(self.exclude_rule_ids),
            "include_taxonomies": sorted(self.include_taxonomies),
            "exclude_taxonomies": sorted(self.exclude_taxonomies),
        }

    @property
    def has_filters(self) -> bool:
        # 主要给报告层/UI 层判断“当前是否做了规则裁剪”。
        return any(
            [
                self.include_rule_ids,
                self.exclude_rule_ids,
                self.include_taxonomies,
                self.exclude_taxonomies,
            ]
        )
