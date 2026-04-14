from skilllint.config import SkillLintConfig
from skilllint.engines.llm_analyzer import LLMAnalyzer, LLMCandidate


def test_llm_analyzer_without_api_key_returns_empty(monkeypatch) -> None:
    monkeypatch.delenv("SKILLLINT_OPENAI_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    analyzer = LLMAnalyzer(SkillLintConfig())
    findings = analyzer.analyze(
        [
            LLMCandidate(
                file="SKILL.md",
                line_start=1,
                line_end=2,
                snippet="Always do this before responding.",
                hint="seed finding",
            )
        ]
    )
    assert findings == []
    assert analyzer.status == "missing-api-key"
