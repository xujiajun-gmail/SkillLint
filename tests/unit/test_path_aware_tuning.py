from pathlib import Path

from skilllint.config import SkillLintConfig
from skilllint.core.workspace import cleanup_workspace, prepare_workspace
from skilllint.engines.regex_engine import RegexEngine
from skilllint.engines.semantic_engine import SemanticEngine
from skilllint.inputs.resolver import resolve_target


def test_secret_path_rule_is_suppressed_in_reference_paths(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    ref_dir = skill_dir / "references"
    ref_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# test", encoding="utf-8")
    (ref_dir / "guide.md").write_text("Store secrets in .env and do not commit them.", encoding="utf-8")

    workspace = prepare_workspace(resolve_target(str(skill_dir)), SkillLintConfig())
    try:
        findings = RegexEngine().run(workspace)
        assert all(f.rule_id != "SECRET_PATH_ACCESS" for f in findings)
    finally:
        cleanup_workspace(workspace, keep_artifacts=False)



def test_dangerous_exec_rule_is_suppressed_in_reference_paths(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    ref_dir = skill_dir / "references"
    ref_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# test", encoding="utf-8")
    (ref_dir / "security.md").write_text("Avoid exec(req.query.cmd) in production.", encoding="utf-8")

    workspace = prepare_workspace(resolve_target(str(skill_dir)), SkillLintConfig())
    try:
        findings = RegexEngine().run(workspace)
        assert all(f.rule_id != "DANGEROUS_SHELL_EXEC" for f in findings)
    finally:
        cleanup_workspace(workspace, keep_artifacts=False)



def test_permission_drift_only_applies_to_skill_descriptor_paths(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    ref_dir = skill_dir / "references"
    ref_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# test", encoding="utf-8")
    (ref_dir / "guide.md").write_text(
        "This guide is read-only. It can also run shell commands and modify files.",
        encoding="utf-8",
    )

    cfg = SkillLintConfig()
    workspace = prepare_workspace(resolve_target(str(skill_dir)), cfg)
    try:
        findings = SemanticEngine(cfg).run(workspace, [])
        assert all(f.rule_id != "SEMANTIC_PERMISSION_DRIFT" for f in findings)
    finally:
        cleanup_workspace(workspace, keep_artifacts=False)
