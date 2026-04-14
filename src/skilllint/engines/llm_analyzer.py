from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any
from uuid import uuid4

from skilllint.config import SkillLintConfig
from skilllint.models import Confidence, Evidence, Finding, Severity


@dataclass(frozen=True)
class LLMCandidate:
    file: str
    line_start: int | None
    line_end: int | None
    snippet: str
    hint: str


class LLMAnalyzer:
    """Optional OpenAI-compatible semantic analyzer.

    The analyzer is intentionally conservative: it only reviews a small number
    of already suspicious snippets and may return zero findings.
    """

    def __init__(self, config: SkillLintConfig) -> None:
        self.config = config
        self._client: Any | None = None
        self._status = "disabled"

    @property
    def status(self) -> str:
        return self._status

    def analyze(self, candidates: list[LLMCandidate]) -> list[Finding]:
        if not candidates:
            self._status = "no-candidates"
            return []
        client = self._get_client()
        if client is None:
            return []

        findings: list[Finding] = []
        for candidate in candidates[:6]:
            response_data = self._analyze_candidate(client, candidate)
            for item in response_data.get("findings", []):
                severity = _normalize_severity(item.get("severity"))
                confidence = _normalize_confidence(item.get("confidence"))
                findings.append(
                    Finding(
                        id=str(uuid4()),
                        rule_id="LLM_SEMANTIC_REVIEW",
                        title=item.get("title") or "LLM semantic finding",
                        severity=severity,
                        confidence=confidence,
                        engine="semantic-llm",
                        primary_taxonomy=item.get("primary_taxonomy"),
                        related_taxonomy=item.get("related_taxonomy") or [],
                        secondary_tags=["semantic", "llm"],
                        explanation=item.get("explanation"),
                        remediation=item.get("remediation"),
                        evidence=Evidence(
                            file=candidate.file,
                            line_start=candidate.line_start,
                            line_end=candidate.line_end,
                            snippet=candidate.snippet,
                        ),
                        metadata={"hint": candidate.hint},
                    )
                )
        self._status = "used"
        return findings

    def _get_client(self) -> Any | None:
        api_key = os.getenv("SKILLLINT_OPENAI_API_KEY") or os.getenv("OPENAI_API_KEY")
        if not api_key:
            self._status = "missing-api-key"
            return None
        try:
            from openai import OpenAI
        except Exception:
            self._status = "openai-import-failed"
            return None

        if self._client is None:
            base_url = os.getenv("SKILLLINT_OPENAI_BASE_URL") or os.getenv("OPENAI_BASE_URL")
            kwargs: dict[str, Any] = {"api_key": api_key}
            if base_url:
                kwargs["base_url"] = base_url
            self._client = OpenAI(**kwargs)
        return self._client

    def _analyze_candidate(self, client: Any, candidate: LLMCandidate) -> dict[str, Any]:
        prompt = _build_prompt(candidate)
        try:
            response = client.chat.completions.create(
                model=self.config.llm.model,
                temperature=self.config.llm.temperature,
                response_format={"type": "json_object"},
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a security analyzer for agent skills. "
                            "Only report concrete, snippet-grounded findings. "
                            "Return JSON with a top-level 'findings' array."
                        ),
                    },
                    {"role": "user", "content": prompt},
                ],
            )
            content = response.choices[0].message.content or '{"findings": []}'
            return json.loads(content)
        except Exception as exc:
            self._status = f"llm-error:{type(exc).__name__}"
            return {"findings": []}


def _build_prompt(candidate: LLMCandidate) -> str:
    return f"""
Review this skill snippet and decide whether it contains a likely security issue.

Allowed taxonomy codes:
- SLT-A01, SLT-A02, SLT-A03, SLT-A04, SLT-A05
- SLT-B01, SLT-B03, SLT-B05, SLT-B06
- SLT-C01, SLT-C02, SLT-C03, SLT-C04
- SLT-D01
- SLT-E01, SLT-E02, SLT-E03

Rules:
- Report zero findings if the snippet looks benign or ambiguous.
- Only use evidence from this snippet.
- Keep explanations short and concrete.

Return JSON:
{{
  "findings": [
    {{
      "title": "...",
      "severity": "low|medium|high|critical",
      "confidence": "low|medium|high",
      "primary_taxonomy": "SLT-...",
      "related_taxonomy": ["SLT-..."],
      "explanation": "...",
      "remediation": "..."
    }}
  ]
}}

File: {candidate.file}
Line range: {candidate.line_start}-{candidate.line_end}
Hint: {candidate.hint}
Snippet:
{candidate.snippet}
""".strip()


def _normalize_severity(value: Any) -> Severity:
    if value in {"info", "low", "medium", "high", "critical"}:
        return value
    return "medium"


def _normalize_confidence(value: Any) -> Confidence:
    if value in {"low", "medium", "high"}:
        return value
    return "medium"
