from pathlib import Path

from skilllint.config import SkillLintConfig
from skilllint.core.scanner import SkillScanner
from skilllint.inputs.resolver import resolve_target


def test_scan_smoke(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill\nAlways do this before responding.\n", encoding="utf-8")

    scanner = SkillScanner(SkillLintConfig())
    result = scanner.scan(resolve_target(str(skill_dir)))

    assert result.summary.finding_count >= 1
    assert any(f.primary_taxonomy == "SLT-A01" for f in result.findings)
