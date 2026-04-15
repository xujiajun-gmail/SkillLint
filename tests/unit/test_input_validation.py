from __future__ import annotations

import zipfile
from pathlib import Path

import pytest

from skilllint.config import SkillLintConfig
from skilllint.core.input_validation import InputValidationError
from skilllint.core.scanner import SkillScanner
from skilllint.core.workspace import cleanup_workspace, prepare_workspace
from skilllint.inputs.resolver import resolve_target


def test_prepare_workspace_rejects_directory_without_skill_md(tmp_path: Path) -> None:
    skill_dir = tmp_path / "not-a-skill"
    skill_dir.mkdir()
    (skill_dir / "README.md").write_text("hello", encoding="utf-8")

    with pytest.raises(InputValidationError, match="SKILL.md"):
        prepare_workspace(resolve_target(str(skill_dir)), SkillLintConfig())


def test_prepare_workspace_rejects_too_many_files(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text("# Test Skill", encoding="utf-8")
    for index in range(1000):
        (skill_dir / f"file-{index}.txt").write_text("x", encoding="utf-8")

    with pytest.raises(InputValidationError, match="too many files"):
        prepare_workspace(resolve_target(str(skill_dir)), SkillLintConfig())


def test_prepare_workspace_accepts_single_wrapper_directory(tmp_path: Path) -> None:
    outer = tmp_path / "outer"
    inner = outer / "wrapped-skill"
    inner.mkdir(parents=True)
    (inner / "SKILL.md").write_text("# Wrapped Skill", encoding="utf-8")
    (inner / "helper.py").write_text("print('ok')", encoding="utf-8")

    workspace = prepare_workspace(resolve_target(str(outer)), SkillLintConfig())
    try:
        assert workspace.normalized_dir.name == "normalized"
        assert (workspace.normalized_dir / "SKILL.md").exists()
        assert (workspace.normalized_dir / "helper.py").exists()
    finally:
        cleanup_workspace(workspace, keep_artifacts=False)


def test_prepare_workspace_rejects_zip_without_skill_md(tmp_path: Path) -> None:
    archive = tmp_path / "bad.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("README.md", "hello")

    with pytest.raises(InputValidationError, match="SKILL.md"):
        prepare_workspace(resolve_target(str(archive)), SkillLintConfig())


def test_prepare_workspace_rejects_zip_path_traversal(tmp_path: Path) -> None:
    archive = tmp_path / "traversal.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("../SKILL.md", "# Test Skill")

    with pytest.raises(InputValidationError, match="unsafe path traversal"):
        prepare_workspace(resolve_target(str(archive)), SkillLintConfig())


def test_scanner_rejects_archive_with_too_many_files(tmp_path: Path) -> None:
    archive = tmp_path / "many.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("SKILL.md", "# Test Skill")
        for index in range(1000):
            zf.writestr(f"docs/file-{index}.txt", "x")

    with pytest.raises(InputValidationError, match="too many files"):
        SkillScanner(SkillLintConfig()).scan(resolve_target(str(archive)))
