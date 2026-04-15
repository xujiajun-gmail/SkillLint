import zipfile
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


def test_scan_zip_ignores_macos_noise_artifacts(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill-src"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "# Test Skill\nAlways do this before responding.\n",
        encoding="utf-8",
    )

    archive = tmp_path / "skill.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(skill_dir / "SKILL.md", "SKILL.md")
        zf.writestr("__MACOSX/._SKILL.md", b"\x00\x05\x16\x07")
        zf.writestr("__MACOSX/.DS_Store", b"\x00\x01binary")

    scanner = SkillScanner(SkillLintConfig())
    result = scanner.scan(resolve_target(str(archive)))

    assert result.summary.finding_count >= 1
    assert all(
        not (finding.evidence.file or "").startswith("__MACOSX/")
        for finding in result.findings
    )
    assert all(
        finding.rule_id != "PACKAGE_BINARY_PRESENT" or "__MACOSX/" not in (finding.evidence.file or "")
        for finding in result.findings
    )


def test_scan_zip_ignores_windows_noise_artifacts(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill-src"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "# Test Skill\nAlways do this before responding.\n",
        encoding="utf-8",
    )

    archive = tmp_path / "skill-win.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.write(skill_dir / "SKILL.md", "SKILL.md")
        zf.writestr("Thumbs.db", b"\x00\x01binary")
        zf.writestr("Desktop.ini", "[.ShellClassInfo]\nIconResource=test.ico,0\n")

    scanner = SkillScanner(SkillLintConfig())
    result = scanner.scan(resolve_target(str(archive)))

    assert result.summary.finding_count >= 1
    assert all(
        (finding.evidence.file or "") not in {"Thumbs.db", "Desktop.ini"}
        for finding in result.findings
    )
