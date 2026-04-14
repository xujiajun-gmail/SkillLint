from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RuleSelector:
    include_rule_ids: set[str] = field(default_factory=set)
    exclude_rule_ids: set[str] = field(default_factory=set)
    include_taxonomies: set[str] = field(default_factory=set)
    exclude_taxonomies: set[str] = field(default_factory=set)

    def allows_rule(self, rule_id: str, taxonomy: str | None = None) -> bool:
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
        return any(
            [
                self.include_rule_ids,
                self.exclude_rule_ids,
                self.include_taxonomies,
                self.exclude_taxonomies,
            ]
        )
