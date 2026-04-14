from __future__ import annotations

from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel, Field

from skilllint.config import load_config
from skilllint.core.scanner import SkillScanner
from skilllint.inputs.resolver import resolve_target
from skilllint.models import ScanResult, Severity, severity_rank

Verdict = Literal["safe", "needs_review", "suspicious", "malicious"]


class GoldenSample(BaseModel):
    sample_id: str
    local_path: str
    source_alias: str | None = None
    community: str | None = None
    expected_verdict: Verdict
    expected_min_risk: Severity = "info"
    expected_rules_present: list[str] = Field(default_factory=list)
    expected_rules_absent: list[str] = Field(default_factory=list)
    expected_taxonomies_present: list[str] = Field(default_factory=list)
    expected_taxonomies_absent: list[str] = Field(default_factory=list)
    rationale: str = ""
    notes: str | None = None


class GoldenDataset(BaseModel):
    version: int = 1
    profile: str = "balanced"
    description: str | None = None
    samples: list[GoldenSample] = Field(default_factory=list)


class RuleMetric(BaseModel):
    tp: int = 0
    fp: int = 0
    fn: int = 0
    tn: int = 0
    support_positive: int = 0
    support_negative: int = 0
    precision: float = 0.0
    recall: float = 0.0
    f1: float = 0.0


class GoldenEvaluationResult(BaseModel):
    generated_at: str
    dataset_path: str
    profile: str
    sample_count: int
    verdict_accuracy: float
    risk_min_accuracy: float
    rule_micro: RuleMetric
    taxonomy_micro: RuleMetric
    verdict_confusion: dict[str, dict[str, int]]
    sample_results: list[dict] = Field(default_factory=list)
    rule_metrics: dict[str, RuleMetric] = Field(default_factory=dict)
    taxonomy_metrics: dict[str, RuleMetric] = Field(default_factory=dict)


def load_golden_dataset(path: Path) -> GoldenDataset:
    return GoldenDataset.model_validate(yaml.safe_load(path.read_text(encoding="utf-8")) or {})


def evaluate_golden_dataset(
    root: Path,
    dataset_path: Path,
    *,
    profile: str | None = None,
    config_path: Path | None = None,
) -> GoldenEvaluationResult:
    dataset = load_golden_dataset(dataset_path)
    selected_profile = profile or dataset.profile
    scanner = SkillScanner(load_config(config_path, profile=selected_profile))

    verdict_matches = 0
    risk_matches = 0
    verdict_confusion: dict[str, Counter[str]] = defaultdict(Counter)
    rule_counts: dict[str, Counter[str]] = defaultdict(Counter)
    taxonomy_counts: dict[str, Counter[str]] = defaultdict(Counter)
    sample_results: list[dict] = []

    for sample in dataset.samples:
        target_path = root / sample.local_path
        result = scanner.scan(resolve_target(str(target_path)))
        predicted_rules = {finding.rule_id for finding in result.findings}
        predicted_taxonomies = {finding.primary_taxonomy for finding in result.findings if finding.primary_taxonomy}

        verdict_match = result.summary.verdict == sample.expected_verdict
        risk_match = severity_rank(result.summary.risk_level) >= severity_rank(sample.expected_min_risk)
        if verdict_match:
            verdict_matches += 1
        if risk_match:
            risk_matches += 1
        verdict_confusion[sample.expected_verdict][result.summary.verdict] += 1

        expected_rule_misses = sorted(set(sample.expected_rules_present) - predicted_rules)
        unexpected_rules = sorted(set(sample.expected_rules_absent) & predicted_rules)
        expected_taxonomy_misses = sorted(set(sample.expected_taxonomies_present) - predicted_taxonomies)
        unexpected_taxonomies = sorted(set(sample.expected_taxonomies_absent) & predicted_taxonomies)

        _update_presence_metrics(rule_counts, sample.expected_rules_present, predicted_rules, present=True)
        _update_presence_metrics(rule_counts, sample.expected_rules_absent, predicted_rules, present=False)
        _update_presence_metrics(taxonomy_counts, sample.expected_taxonomies_present, predicted_taxonomies, present=True)
        _update_presence_metrics(taxonomy_counts, sample.expected_taxonomies_absent, predicted_taxonomies, present=False)

        sample_results.append(
            _sample_result_record(
                sample=sample,
                result=result,
                verdict_match=verdict_match,
                risk_match=risk_match,
                expected_rule_misses=expected_rule_misses,
                unexpected_rules=unexpected_rules,
                expected_taxonomy_misses=expected_taxonomy_misses,
                unexpected_taxonomies=unexpected_taxonomies,
            )
        )

    rule_metrics = {name: _finalize_metric(counter) for name, counter in sorted(rule_counts.items())}
    taxonomy_metrics = {name: _finalize_metric(counter) for name, counter in sorted(taxonomy_counts.items())}
    return GoldenEvaluationResult(
        generated_at=datetime.now(UTC).isoformat(),
        dataset_path=str(dataset_path),
        profile=selected_profile,
        sample_count=len(dataset.samples),
        verdict_accuracy=_safe_ratio(verdict_matches, len(dataset.samples)),
        risk_min_accuracy=_safe_ratio(risk_matches, len(dataset.samples)),
        rule_micro=_aggregate_metrics(rule_counts),
        taxonomy_micro=_aggregate_metrics(taxonomy_counts),
        verdict_confusion={key: dict(sorted(value.items())) for key, value in sorted(verdict_confusion.items())},
        sample_results=sample_results,
        rule_metrics=rule_metrics,
        taxonomy_metrics=taxonomy_metrics,
    )


def render_evaluation_markdown(result: GoldenEvaluationResult) -> str:
    lines = [
        "# SkillLint Golden Evaluation",
        "",
        f"- Generated at: `{result.generated_at}`",
        f"- Dataset: `{result.dataset_path}`",
        f"- Profile: `{result.profile}`",
        f"- Sample count: `{result.sample_count}`",
        f"- Verdict accuracy: `{result.verdict_accuracy:.3f}`",
        f"- Risk minimum accuracy: `{result.risk_min_accuracy:.3f}`",
        "",
        "## Rule-level Micro Metrics",
        "",
        _metric_line(result.rule_micro),
        "",
        "## Taxonomy-level Micro Metrics",
        "",
        _metric_line(result.taxonomy_micro),
        "",
        "## Verdict Confusion",
        "",
    ]
    for expected, predicted_counts in result.verdict_confusion.items():
        lines.append(f"### expected={expected}")
        lines.append("")
        for predicted, count in predicted_counts.items():
            lines.append(f"- predicted `{predicted}`: {count}")
        lines.append("")

    mismatches = [sample for sample in result.sample_results if not sample["verdict_match"] or not sample["risk_match"] or sample["expected_rule_misses"] or sample["unexpected_rules"] or sample["expected_taxonomy_misses"] or sample["unexpected_taxonomies"]]
    lines.extend(["## Sample Mismatches", ""])
    if not mismatches:
        lines.append("No mismatches detected.")
    else:
        for sample in mismatches:
            lines.extend(
                [
                    f"### {sample['sample_id']}",
                    "",
                    f"- path: `{sample['local_path']}`",
                    f"- expected verdict/risk: `{sample['expected_verdict']}` / `{sample['expected_min_risk']}`",
                    f"- predicted verdict/risk: `{sample['predicted_verdict']}` / `{sample['predicted_risk']}`",
                    f"- aggregate score: `{sample['aggregate_score']}`",
                ]
            )
            for key in [
                "expected_rule_misses",
                "unexpected_rules",
                "expected_taxonomy_misses",
                "unexpected_taxonomies",
            ]:
                values = sample[key]
                if values:
                    lines.append(f"- {key}: `{', '.join(values)}`")
            if sample.get("rationale"):
                lines.append(f"- rationale: {sample['rationale']}")
            lines.append("")

    lines.extend(["## Lowest Precision Rules", ""])
    for rule_id, metric in _sorted_problem_metrics(result.rule_metrics, field="precision")[:10]:
        lines.append(f"- `{rule_id}`: {_metric_line(metric)}")
    lines.extend(["", "## Lowest Recall Rules", ""])
    for rule_id, metric in _sorted_problem_metrics(result.rule_metrics, field="recall")[:10]:
        lines.append(f"- `{rule_id}`: {_metric_line(metric)}")
    return "\n".join(lines).strip() + "\n"


def _sample_result_record(
    *,
    sample: GoldenSample,
    result: ScanResult,
    verdict_match: bool,
    risk_match: bool,
    expected_rule_misses: list[str],
    unexpected_rules: list[str],
    expected_taxonomy_misses: list[str],
    unexpected_taxonomies: list[str],
) -> dict:
    predicted_taxonomies = sorted({finding.primary_taxonomy for finding in result.findings if finding.primary_taxonomy})
    return {
        "sample_id": sample.sample_id,
        "local_path": sample.local_path,
        "expected_verdict": sample.expected_verdict,
        "expected_min_risk": sample.expected_min_risk,
        "predicted_verdict": result.summary.verdict,
        "predicted_risk": result.summary.risk_level,
        "aggregate_score": result.summary.aggregate_score,
        "verdict_match": verdict_match,
        "risk_match": risk_match,
        "predicted_rules": [finding.rule_id for finding in result.findings],
        "predicted_taxonomies": predicted_taxonomies,
        "expected_rule_misses": expected_rule_misses,
        "unexpected_rules": unexpected_rules,
        "expected_taxonomy_misses": expected_taxonomy_misses,
        "unexpected_taxonomies": unexpected_taxonomies,
        "rationale": sample.rationale,
    }


def _update_presence_metrics(
    counts: dict[str, Counter[str]],
    labels: list[str],
    predicted: set[str],
    *,
    present: bool,
) -> None:
    for label in labels:
        metric = counts[label]
        if present:
            metric["support_positive"] += 1
            if label in predicted:
                metric["tp"] += 1
            else:
                metric["fn"] += 1
        else:
            metric["support_negative"] += 1
            if label in predicted:
                metric["fp"] += 1
            else:
                metric["tn"] += 1


def _aggregate_metrics(counts: dict[str, Counter[str]]) -> RuleMetric:
    aggregate = Counter()
    for counter in counts.values():
        aggregate.update(counter)
    return _finalize_metric(aggregate)


def _finalize_metric(counter: Counter[str]) -> RuleMetric:
    tp = counter.get("tp", 0)
    fp = counter.get("fp", 0)
    fn = counter.get("fn", 0)
    precision = _safe_ratio(tp, tp + fp)
    recall = _safe_ratio(tp, tp + fn)
    return RuleMetric(
        tp=tp,
        fp=fp,
        fn=fn,
        tn=counter.get("tn", 0),
        support_positive=counter.get("support_positive", 0),
        support_negative=counter.get("support_negative", 0),
        precision=precision,
        recall=recall,
        f1=_safe_ratio(2 * precision * recall, precision + recall),
    )


def _safe_ratio(numerator: float, denominator: float) -> float:
    if denominator == 0:
        return 0.0
    return numerator / denominator


def _metric_line(metric: RuleMetric) -> str:
    return (
        f"precision={metric.precision:.3f}, recall={metric.recall:.3f}, f1={metric.f1:.3f}, "
        f"tp={metric.tp}, fp={metric.fp}, fn={metric.fn}, support+={metric.support_positive}, support-={metric.support_negative}"
    )


def _sorted_problem_metrics(metrics: dict[str, RuleMetric], *, field: str) -> list[tuple[str, RuleMetric]]:
    filtered = [(name, metric) for name, metric in metrics.items() if metric.support_positive or metric.support_negative]
    return sorted(filtered, key=lambda item: (getattr(item[1], field), item[0]))
