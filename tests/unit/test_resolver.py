from pathlib import Path

from skilllint.inputs.resolver import resolve_target


def test_resolve_directory(tmp_path: Path) -> None:
    info = resolve_target(str(tmp_path))
    assert info.normalized_type == "directory"


def test_resolve_zip(tmp_path: Path) -> None:
    archive = tmp_path / "sample.zip"
    archive.write_bytes(b"PK\x03\x04")
    info = resolve_target(str(archive))
    assert info.normalized_type == "zip"


def test_resolve_url() -> None:
    info = resolve_target("https://example.com/skill.zip")
    assert info.normalized_type == "url"


def test_resolve_git_url() -> None:
    info = resolve_target("https://github.com/openai/skills")
    assert info.normalized_type == "git"
