from __future__ import annotations

import ipaddress
import posixpath
import stat
from pathlib import Path, PurePosixPath
from typing import Any
from urllib.parse import urlparse
from zipfile import ZipInfo

from skilllint.config import SkillLintConfig
from skilllint.utils.files import IGNORED_DIRS, is_ignored_noise_artifact, iter_files

REMOTE_METADATA_HOSTS = {"169.254.169.254", "metadata.google.internal", "100.100.100.200"}


class InputValidationError(ValueError):
    """在扫描开始前发现输入不满足 SkillLint 接受条件时抛出。"""

    def __init__(self, code: str, message: str, *, metadata: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.metadata = metadata or {}

    def to_api_detail(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "message": self.message,
            "metadata": self.metadata,
        }


def validation_error(code: str, message: str, **metadata: Any) -> InputValidationError:
    return InputValidationError(code=code, message=message, metadata=metadata or None)


def select_skill_root(root: Path) -> Path:
    """尝试自动下钻单层/多层包装目录，找到真正的 skill 根。

    常见场景：
    - 用户上传的 zip 外面多包了一层目录；
    - 用户把“项目父目录”而不是 skill 根目录传给扫描器。

    仅当当前目录：
    - 不含有效顶层文件；
    - 且只有一个非噪声子目录；
    才会自动继续下钻。这样可以降低误判风险。
    """
    current = root
    while True:
        entries = list(current.iterdir())
        child_dirs = [
            entry
            for entry in entries
            if entry.is_dir() and entry.name not in IGNORED_DIRS and not is_ignored_noise_artifact(entry)
        ]
        child_files = [
            entry
            for entry in entries
            if entry.is_file() and not is_ignored_noise_artifact(entry)
        ]
        if (current / "SKILL.md").exists():
            return current
        if child_files or len(child_dirs) != 1:
            return current
        current = child_dirs[0]


def validate_skill_tree(root: Path, config: SkillLintConfig) -> None:
    """校验一个已经落盘的目录是否可作为单个 skill 扫描。"""
    files = iter_files(root)
    if not files:
        raise validation_error("empty_input", "Input directory is empty after normalization.")
    if len(files) > config.inputs.max_input_files:
        raise validation_error(
            "too_many_files",
            f"Input contains too many files: {len(files)} > {config.inputs.max_input_files}.",
            file_count=len(files),
            max_input_files=config.inputs.max_input_files,
        )
    if config.inputs.require_skill_entry:
        nested_skill_files = [path for path in files if path.name == "SKILL.md"]
        if not nested_skill_files:
            raise validation_error("missing_skill_entry", "Input is not a skill package: no SKILL.md was found.")
        skill_file = root / "SKILL.md"
        if (not skill_file.exists() or not skill_file.is_file()) and len(nested_skill_files) == 1:
            raise validation_error(
                "missing_root_skill_entry",
                "Input does not look like a skill root: root SKILL.md is missing."
            )

    total_bytes = 0
    max_single_file_bytes = config.inputs.max_single_file_mb * 1024 * 1024
    max_total_bytes = config.inputs.max_total_input_mb * 1024 * 1024
    for path in files:
        try:
            rel = path.relative_to(root)
            size = path.stat().st_size
        except OSError as exc:  # pragma: no cover
            raise validation_error("input_inspection_failed", f"Unable to inspect input file: {path}") from exc
        if len(rel.as_posix()) > config.inputs.max_path_length:
            raise validation_error(
                "path_too_long",
                f"Input path is too long: {rel.as_posix()} ({len(rel.as_posix())} > {config.inputs.max_path_length}).",
                path=rel.as_posix(),
                path_length=len(rel.as_posix()),
                max_path_length=config.inputs.max_path_length,
            )
        if len(rel.parts) > config.inputs.max_path_depth:
            raise validation_error(
                "path_too_deep",
                f"Input path is too deep: {rel.as_posix()} ({len(rel.parts)} > {config.inputs.max_path_depth}).",
                path=rel.as_posix(),
                path_depth=len(rel.parts),
                max_path_depth=config.inputs.max_path_depth,
            )
        if size > max_single_file_bytes:
            raise validation_error(
                "file_too_large",
                f"Input file is too large: {rel.as_posix()} ({size} bytes > {max_single_file_bytes} bytes).",
                path=rel.as_posix(),
                file_size=size,
                max_single_file_bytes=max_single_file_bytes,
            )
        total_bytes += size
        if total_bytes > max_total_bytes:
            raise validation_error(
                "input_too_large",
                f"Input is too large after normalization: {total_bytes} bytes > {max_total_bytes} bytes.",
                total_bytes=total_bytes,
                max_total_bytes=max_total_bytes,
            )


def validate_local_directory_source(root: Path, config: SkillLintConfig) -> Path:
    """在复制目录前，先对源目录做轻量校验并确定 skill 根。"""
    skill_root = select_skill_root(root)
    validate_skill_tree(skill_root, config)
    return skill_root


def validate_remote_source_url(url: str) -> None:
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"}:
        raise validation_error("unsupported_remote_scheme", f"Unsupported remote URL scheme: {parsed.scheme or '<missing>'}.")
    if not parsed.hostname:
        raise validation_error("invalid_remote_url", "Remote URL must include a valid hostname.")
    if parsed.username or parsed.password:
        raise validation_error("remote_credentials_not_allowed", "Remote URL must not contain embedded credentials.")
    host = parsed.hostname.lower()
    if host in {"localhost"} or host.endswith(".local"):
        raise validation_error("unsafe_remote_host", f"Remote URL host is not allowed: {host}.", host=host)
    if host in REMOTE_METADATA_HOSTS:
        raise validation_error("unsafe_remote_host", f"Remote URL host is not allowed: {host}.", host=host)
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return
    if ip.is_loopback or ip.is_private or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        raise validation_error("unsafe_remote_host", f"Remote URL host is not allowed: {host}.", host=host)


def validate_zip_members(infos: list[ZipInfo], config: SkillLintConfig) -> None:
    """在真正解压前，对 zip 成员做路径与规模校验。"""
    max_files = config.inputs.max_input_files
    max_single_file_bytes = config.inputs.max_single_file_mb * 1024 * 1024
    max_total_bytes = config.inputs.max_total_input_mb * 1024 * 1024
    counted_files = 0
    total_bytes = 0
    for info in infos:
        raw_name = info.filename
        if not raw_name or raw_name.endswith("/"):
            continue
        normalized = _safe_archive_member(raw_name, config)
        if is_ignored_noise_artifact(Path(normalized)):
            continue
        if _zip_info_is_symlink(info):
            raise validation_error(
                "archive_symlink_entry",
                f"Archive contains unsupported symlink entry: {raw_name}",
                path=raw_name,
            )
        counted_files += 1
        if counted_files > max_files:
            raise validation_error(
                "too_many_files",
                f"Archive contains too many files: {counted_files} > {max_files}.",
                file_count=counted_files,
                max_input_files=max_files,
            )
        if info.file_size > max_single_file_bytes:
            raise validation_error(
                "file_too_large",
                f"Archive file is too large: {normalized} ({info.file_size} bytes > {max_single_file_bytes} bytes).",
                path=normalized,
                file_size=info.file_size,
                max_single_file_bytes=max_single_file_bytes,
            )
        total_bytes += info.file_size
        if total_bytes > max_total_bytes:
            raise validation_error(
                "input_too_large",
                f"Archive is too large after extraction: {total_bytes} bytes > {max_total_bytes} bytes.",
                total_bytes=total_bytes,
                max_total_bytes=max_total_bytes,
            )


def safe_archive_path(name: str, config: SkillLintConfig) -> Path:
    """把压缩包成员名转换为安全的相对路径。"""
    return Path(_safe_archive_member(name, config))


def _safe_archive_member(name: str, config: SkillLintConfig) -> str:
    normalized = posixpath.normpath(name.replace("\\", "/"))
    if normalized in {"", "."}:
        raise validation_error("invalid_archive_entry", "Archive contains an empty path entry.")
    if normalized.startswith("/") or normalized.startswith("../") or "/../" in normalized:
        raise validation_error(
            "unsafe_archive_path",
            f"Archive contains unsafe path traversal entry: {name}",
            path=name,
        )
    parts = [part for part in PurePosixPath(normalized).parts if part not in {"", "."}]
    if not parts:
        raise validation_error("invalid_archive_entry", "Archive contains an invalid path entry.")
    rel = "/".join(parts)
    if len(rel) > config.inputs.max_path_length:
        raise validation_error(
            "path_too_long",
            f"Archive path is too long: {rel} ({len(rel)} > {config.inputs.max_path_length}).",
            path=rel,
            path_length=len(rel),
            max_path_length=config.inputs.max_path_length,
        )
    if len(parts) > config.inputs.max_path_depth:
        raise validation_error(
            "path_too_deep",
            f"Archive path is too deep: {rel} ({len(parts)} > {config.inputs.max_path_depth}).",
            path=rel,
            path_depth=len(parts),
            max_path_depth=config.inputs.max_path_depth,
        )
    if parts[0].endswith(":"):
        raise validation_error(
            "unsafe_archive_path",
            f"Archive contains invalid drive-qualified path: {name}",
            path=name,
        )
    return rel


def _zip_info_is_symlink(info: ZipInfo) -> bool:
    mode = info.external_attr >> 16
    return stat.S_ISLNK(mode)
