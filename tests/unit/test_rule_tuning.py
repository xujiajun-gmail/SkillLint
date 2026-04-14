from pathlib import Path

from skilllint.config import SkillLintConfig
from skilllint.core.workspace import cleanup_workspace, prepare_workspace
from skilllint.engines.regex_engine import RegexEngine
from skilllint.engines.semantic_engine import SemanticEngine
from skilllint.inputs.resolver import resolve_target


def test_secret_path_regex_does_not_flag_object_env_property(tmp_path: Path) -> None:
    skill_dir = tmp_path / 'skill'
    skill_dir.mkdir()
    (skill_dir / 'api.md').write_text(
        'const result = await this.env.AI.run("model", { prompt });',
        encoding='utf-8',
    )
    (skill_dir / 'SKILL.md').write_text('# test', encoding='utf-8')

    workspace = prepare_workspace(resolve_target(str(skill_dir)), SkillLintConfig())
    try:
        findings = RegexEngine().run(workspace)
        assert all(f.rule_id != 'SECRET_PATH_ACCESS' for f in findings)
    finally:
        cleanup_workspace(workspace, keep_artifacts=False)



def test_dangerous_exec_regex_does_not_flag_generic_sql_exec_calls(tmp_path: Path) -> None:
    skill_dir = tmp_path / 'skill'
    skill_dir.mkdir()
    (skill_dir / 'db.ts').write_text(
        "this.sql.exec('SELECT * FROM users WHERE id = ?', id)",
        encoding='utf-8',
    )
    (skill_dir / 'SKILL.md').write_text('# test', encoding='utf-8')

    workspace = prepare_workspace(resolve_target(str(skill_dir)), SkillLintConfig())
    try:
        findings = RegexEngine().run(workspace)
        assert all(f.rule_id != 'DANGEROUS_SHELL_EXEC' for f in findings)
    finally:
        cleanup_workspace(workspace, keep_artifacts=False)



def test_semantic_exfil_requires_send_and_data_target_in_same_segment(tmp_path: Path) -> None:
    skill_dir = tmp_path / 'skill'
    skill_dir.mkdir()
    (skill_dir / 'SKILL.md').write_text(
        """
This skill provides support for build tooling.

Refer to https://example.com/docs for supported APIs.
""".strip(),
        encoding='utf-8',
    )

    cfg = SkillLintConfig()
    workspace = prepare_workspace(resolve_target(str(skill_dir)), cfg)
    try:
        findings = SemanticEngine(cfg).run(workspace, [])
        assert all(f.rule_id != 'SEMANTIC_EXFIL_MASQUERADE' for f in findings)
    finally:
        cleanup_workspace(workspace, keep_artifacts=False)


def test_destructive_cleanup_context_is_suppressed(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        """
# Clean install
rm -rf node_modules pnpm-lock.yaml
pnpm install
""".strip(),
        encoding="utf-8",
    )

    workspace = prepare_workspace(resolve_target(str(skill_dir)), SkillLintConfig())
    try:
        findings = RegexEngine().run(workspace)
        assert all(f.rule_id != "DESTRUCTIVE_FILE_OPERATION" for f in findings)
    finally:
        cleanup_workspace(workspace, keep_artifacts=False)



def test_fsevents_dependency_name_is_not_file_monitoring(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        '"pnpm": {"neverBuiltDependencies": ["fsevents"]}',
        encoding="utf-8",
    )

    workspace = prepare_workspace(resolve_target(str(skill_dir)), SkillLintConfig())
    try:
        findings = RegexEngine().run(workspace)
        assert all(f.rule_id != "FILE_MONITORING_OR_WATCHER" for f in findings)
    finally:
        cleanup_workspace(workspace, keep_artifacts=False)


def test_remote_pipe_install_defensive_context_is_suppressed(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "Security note: Do NOT install by piping remote scripts to shell, e.g. curl https://example.com/install.sh | bash.",
        encoding="utf-8",
    )

    workspace = prepare_workspace(resolve_target(str(skill_dir)), SkillLintConfig())
    try:
        findings = RegexEngine().run(workspace)
        assert all(f.rule_id != "INSTALL_CURL_PIPE_SHELL" for f in findings)
    finally:
        cleanup_workspace(workspace, keep_artifacts=False)



def test_semantic_hidden_behavior_defensive_silently_context_is_suppressed(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    skill_dir.mkdir()
    (skill_dir / "SKILL.md").write_text(
        "Do NOT use vercel link here because it may silently link the project as a side effect.",
        encoding="utf-8",
    )

    cfg = SkillLintConfig()
    workspace = prepare_workspace(resolve_target(str(skill_dir)), cfg)
    try:
        findings = SemanticEngine(cfg).run(workspace, [])
        assert all(f.rule_id != "SEMANTIC_HIDDEN_BEHAVIOR" for f in findings)
    finally:
        cleanup_workspace(workspace, keep_artifacts=False)



def test_trigger_hijack_reference_context_is_suppressed(tmp_path: Path) -> None:
    skill_dir = tmp_path / "skill"
    ref_dir = skill_dir / "references"
    ref_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("# test", encoding="utf-8")
    (ref_dir / "queue.md").write_text(
        "The request queue works for any task processing, not just scraping.",
        encoding="utf-8",
    )

    workspace = prepare_workspace(resolve_target(str(skill_dir)), SkillLintConfig())
    try:
        findings = RegexEngine().run(workspace)
        assert all(f.rule_id != "TRIGGER_HIJACK_ANY_TASK" for f in findings)
    finally:
        cleanup_workspace(workspace, keep_artifacts=False)
