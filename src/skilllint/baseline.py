from __future__ import annotations

import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from skilllint.config import load_config
from skilllint.core.scanner import SkillScanner
from skilllint.inputs.resolver import resolve_target
from skilllint.models import ScanResult


@dataclass(frozen=True)
class ExampleTarget:
    name: str
    source_alias: str
    local_path: str
    community: str
    repo: str | None = None
    repo_url: str | None = None
    source_url: str | None = None


def load_example_targets(root: Path) -> list[ExampleTarget]:
    # baseline 语料来自 examples/ 与 examples/zh-community/ 两套索引。
    targets: list[ExampleTarget] = []
    for index_path, community in [
        (root / "examples" / "index.json", "general"),
        (root / "examples" / "zh-community" / "index.json", "zh"),
    ]:
        if not index_path.exists():
            continue
        entries = json.loads(index_path.read_text(encoding="utf-8"))
        for entry in entries:
            targets.append(
                ExampleTarget(
                    name=entry["name"],
                    source_alias=entry["source_alias"],
                    local_path=entry["local_path"],
                    community=entry.get("community", community),
                    repo=entry.get("repo"),
                    repo_url=entry.get("repo_url"),
                    source_url=entry.get("source_url"),
                )
            )
    return sorted(targets, key=lambda item: (item.community, item.source_alias, item.name))


def build_baseline_dataset(
    root: Path,
    *,
    profile: str = "balanced",
    config_path: Path | None = None,
) -> dict:
    # baseline 的目的不是判定恶意，而是形成“当前规则在真实样本上的回归快照”。
    targets = load_example_targets(root)
    cfg = load_config(config_path, profile=profile)
    # baseline 语料更强调“扫描回归稳定性”，允许少量非标准 skill 样本继续进入扫描。
    cfg.inputs.require_skill_entry = False
    scanner = SkillScanner(cfg)

    sample_results: list[dict] = []
    failures: list[dict] = []
    verdicts = Counter()
    risk_levels = Counter()
    taxonomy_counts = Counter()
    rule_counts = Counter()
    total_findings = 0
    source_stats: dict[str, Counter] = defaultdict(Counter)
    community_stats: dict[str, Counter] = defaultdict(Counter)

    for target in targets:
        abs_path = root / target.local_path
        try:
            result = scanner.scan(resolve_target(str(abs_path)))
        except Exception as exc:  # pragma: no cover - defensive baseline collection
            failures.append(
                {
                    "target": target.local_path,
                    "source_alias": target.source_alias,
                    "community": target.community,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue

        sample = _sample_record(target, result)
        sample_results.append(sample)

        verdicts[result.summary.verdict] += 1
        risk_levels[result.summary.risk_level] += 1
        total_findings += result.summary.finding_count
        source_stats[target.source_alias]["samples"] += 1
        source_stats[target.source_alias][f"verdict:{result.summary.verdict}"] += 1
        source_stats[target.source_alias][f"risk:{result.summary.risk_level}"] += 1
        source_stats[target.source_alias]["findings"] += result.summary.finding_count
        community_stats[target.community]["samples"] += 1
        community_stats[target.community][f"verdict:{result.summary.verdict}"] += 1
        community_stats[target.community][f"risk:{result.summary.risk_level}"] += 1
        community_stats[target.community]["findings"] += result.summary.finding_count

        for finding in result.findings:
            if finding.primary_taxonomy:
                taxonomy_counts[finding.primary_taxonomy] += 1
            rule_counts[finding.rule_id] += 1

    sample_results.sort(
        key=lambda item: (
            _severity_rank(item["risk_level"]),
            item["finding_count"],
            item["local_path"],
        ),
        reverse=True,
    )

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "profile": profile,
        "tool_version": sample_results[0]["tool_version"] if sample_results else None,
        "sample_count": len(sample_results),
        "failure_count": len(failures),
        "summary": {
            "total_findings": total_findings,
            "verdicts": dict(sorted(verdicts.items())),
            "risk_levels": dict(sorted(risk_levels.items())),
            "taxonomy_counts": dict(taxonomy_counts.most_common()),
            "rule_counts": dict(rule_counts.most_common()),
        },
        "source_stats": _normalize_counter_map(source_stats),
        "community_stats": _normalize_counter_map(community_stats),
        "top_risky_samples": sample_results[:20],
        "samples": sample_results,
        "failures": failures,
    }



def render_baseline_markdown(dataset: dict) -> str:
    lines = [
        "# SkillLint Example Baseline",
        "",
        f"- Generated at: `{dataset['generated_at']}`",
        f"- Profile: `{dataset['profile']}`",
        f"- Tool version: `{dataset.get('tool_version') or 'unknown'}`",
        f"- Sample count: `{dataset['sample_count']}`",
        f"- Failure count: `{dataset['failure_count']}`",
        f"- Total findings: `{dataset['summary']['total_findings']}`",
        "",
        "> Note: this baseline is a reproducibility dataset and regression snapshot, not a ground-truth maliciousness label set.",
        "> High counts on popular public skills usually indicate rule sensitivity and false-positive tuning opportunities, not confirmed compromise.",
        "",
        "## How to Regenerate",
        "",
        "```bash",
        "python3 scripts/generate_example_baseline.py",
        "```",
        "",
        "## Verdict Distribution",
        "",
    ]
    for verdict, count in dataset["summary"]["verdicts"].items():
        lines.append(f"- `{verdict}`: {count}")
    lines.extend(["", "## Risk Distribution", ""])
    for risk, count in dataset["summary"]["risk_levels"].items():
        lines.append(f"- `{risk}`: {count}")

    lines.extend(["", "## Top Taxonomies", ""])
    for code, count in list(dataset["summary"]["taxonomy_counts"].items())[:15]:
        lines.append(f"- `{code}`: {count}")

    lines.extend(["", "## Top Rules", ""])
    for rule_id, count in list(dataset["summary"]["rule_counts"].items())[:15]:
        lines.append(f"- `{rule_id}`: {count}")

    lines.extend(["", "## By Community", ""])
    for community, stats in sorted(dataset["community_stats"].items()):
        lines.append(f"### {community}")
        lines.append("")
        lines.append(f"- samples: {stats.get('samples', 0)}")
        lines.append(f"- findings: {stats.get('findings', 0)}")
        for key, value in sorted(stats.items()):
            if key.startswith("verdict:") or key.startswith("risk:"):
                lines.append(f"- {key}: {value}")
        lines.append("")

    lines.extend(["## By Source", ""])
    for source_alias, stats in sorted(dataset["source_stats"].items()):
        lines.append(f"### {source_alias}")
        lines.append("")
        lines.append(f"- samples: {stats.get('samples', 0)}")
        lines.append(f"- findings: {stats.get('findings', 0)}")
        for key, value in sorted(stats.items()):
            if key.startswith("verdict:") or key.startswith("risk:"):
                lines.append(f"- {key}: {value}")
        lines.append("")

    lines.extend(["## Top Risky Samples", ""])
    for item in dataset["top_risky_samples"]:
        lines.extend(
            [
                f"### {item['local_path']}",
                "",
                f"- source: `{item['source_alias']}`",
                f"- community: `{item['community']}`",
                f"- risk: `{item['risk_level']}`",
                f"- verdict: `{item['verdict']}`",
                f"- findings: `{item['finding_count']}`",
            ]
        )
        if item["top_taxonomies"]:
            lines.append(f"- top_taxonomies: `{', '.join(item['top_taxonomies'])}`")
        if item["top_rules"]:
            lines.append(f"- top_rules: `{', '.join(item['top_rules'])}`")
        lines.append("")

    if dataset["failures"]:
        lines.extend(["## Failures", ""])
        for failure in dataset["failures"]:
            lines.append(f"- `{failure['target']}`: {failure['error']}")

    return "\n".join(lines).strip() + "\n"



def _sample_record(target: ExampleTarget, result: ScanResult) -> dict:
    # sample record 保留最有代表性的聚合字段，避免 baseline JSON 体积过大。
    taxonomy_counts = Counter(
        finding.primary_taxonomy for finding in result.findings if finding.primary_taxonomy
    )
    rule_counts = Counter(finding.rule_id for finding in result.findings)
    return {
        "name": target.name,
        "source_alias": target.source_alias,
        "community": target.community,
        "local_path": target.local_path,
        "repo": target.repo,
        "repo_url": target.repo_url,
        "source_url": target.source_url,
        "risk_level": result.summary.risk_level,
        "verdict": result.summary.verdict,
        "finding_count": result.summary.finding_count,
        "critical": result.summary.critical,
        "high": result.summary.high,
        "medium": result.summary.medium,
        "low": result.summary.low,
        "info": result.summary.info,
        "tool_version": result.tool_version,
        "top_taxonomies": [code for code, _ in taxonomy_counts.most_common(5)],
        "top_rules": [rule_id for rule_id, _ in rule_counts.most_common(5)],
    }



def _normalize_counter_map(counter_map: dict[str, Counter]) -> dict[str, dict[str, int]]:
    return {key: dict(sorted(counter.items())) for key, counter in sorted(counter_map.items())}



def _severity_rank(severity: str) -> int:
    order = {"info": 0, "low": 1, "medium": 2, "high": 3, "critical": 4}
    return order.get(severity, -1)
