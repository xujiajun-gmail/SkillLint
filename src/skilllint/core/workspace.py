from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse
from uuid import uuid4

import httpx

from skilllint.config import SkillLintConfig
from skilllint.core.input_validation import (
    safe_archive_path,
    select_skill_root,
    validate_local_directory_source,
    validate_remote_source_url,
    validate_skill_tree,
    validate_zip_members,
    validation_error,
)
from skilllint.models import TargetInfo, WorkspaceInfo
from skilllint.utils.files import iter_files


@dataclass
class PreparedWorkspace:
    """一次扫描对应的归一化工作区。

    SkillLint 的设计核心之一是“Normalize First”：
    不论输入是目录、zip、URL 还是 git URL，后续检测器都只面对 normalized_dir。
    """
    scan_id: str
    root_dir: Path
    normalized_dir: Path
    target: TargetInfo
    extracted_from: str | None = None

    def all_files(self) -> list[Path]:
        # workspace 对外暴露“当前归一化目录下所有文件”的统一视图。
        return iter_files(self.normalized_dir)

    def relpath(self, path: Path) -> str:
        # finding/报告层一律使用相对路径，避免把本机绝对路径泄露到输出里。
        return str(path.relative_to(self.normalized_dir))

    def to_model(self) -> WorkspaceInfo:
        return WorkspaceInfo(
            root_dir=str(self.root_dir),
            normalized_dir=str(self.normalized_dir),
            extracted_from=self.extracted_from,
            source_map={},
        )


def prepare_workspace(target: TargetInfo, config: SkillLintConfig) -> PreparedWorkspace:
    # 每次扫描使用独立目录，便于保留工件、复现问题、隔离不同输入。
    scan_id = str(uuid4())
    root_dir = Path(config.workspace.root) / f"scan-{scan_id}"
    root_dir.mkdir(parents=True, exist_ok=True)
    normalized_root = root_dir / "normalized"
    normalized_root.mkdir(parents=True, exist_ok=True)
    normalized_dir = normalized_root

    extracted_from: str | None = None

    if target.normalized_type == "directory":
        source_dir = validate_local_directory_source(Path(target.resolved_path or target.raw), config)
        _copy_directory(source_dir, normalized_dir)
    elif target.normalized_type == "zip":
        archive_path = Path(target.resolved_path or target.raw)
        extracted_from = str(archive_path)
        _validate_local_archive_size(archive_path, config)
        _extract_zip(archive_path, normalized_dir, config)
    elif target.normalized_type == "git":
        _clone_repo(target.resolved_path or target.raw, normalized_dir)
    elif target.normalized_type == "url":
        downloaded = _download_url(target.resolved_path or target.raw, root_dir, config)
        extracted_from = str(downloaded)
        # URL 下载后再按文件类型分流：zip 解压，单文件则直接暂存。
        if downloaded.suffix.lower() == ".zip":
            _extract_zip(downloaded, normalized_dir, config)
        else:
            _stage_single_file(downloaded, normalized_dir)
    else:
        raise ValueError(f"Unsupported target type: {target.normalized_type}")

    normalized_dir = select_skill_root(normalized_root)
    validate_skill_tree(normalized_dir, config)

    return PreparedWorkspace(
        scan_id=scan_id,
        root_dir=root_dir,
        normalized_dir=normalized_dir,
        target=target,
        extracted_from=extracted_from,
    )


def cleanup_workspace(workspace: PreparedWorkspace, keep_artifacts: bool) -> None:
    # 默认清理工作区，避免本地累积大量临时扫描目录；调试时可显式保留。
    if keep_artifacts:
        return
    shutil.rmtree(workspace.root_dir, ignore_errors=True)


def _copy_directory(src: Path, dst: Path) -> None:
    # 这里保留 symlink，而不是强制解引用，原因是：
    # package engine 需要显式看到“包内存在 symlink”这一风险信号。
    for child in src.iterdir():
        target = dst / child.name
        if child.is_dir() and not child.is_symlink():
            shutil.copytree(child, target, symlinks=True)
        else:
            if child.is_symlink():
                link_target = child.readlink()
                target.symlink_to(link_target, target_is_directory=child.is_dir())
            else:
                shutil.copy2(child, target)


def _extract_zip(zip_path: Path, dst: Path, config: SkillLintConfig) -> None:
    # zip 在真正落盘前先做成员级校验，避免 zip slip、过大展开、异常层级等问题。
    try:
        with zipfile.ZipFile(zip_path) as zf:
            infos = zf.infolist()
            validate_zip_members(infos, config)
            for info in infos:
                if info.is_dir():
                    continue
                target = dst / safe_archive_path(info.filename, config)
                target.parent.mkdir(parents=True, exist_ok=True)
                with zf.open(info) as src, target.open("wb") as out:
                    shutil.copyfileobj(src, out)
    except zipfile.BadZipFile as exc:
        raise validation_error("invalid_archive", f"Invalid zip archive: {zip_path}") from exc


def _download_url(url: str, root_dir: Path, config: SkillLintConfig) -> Path:
    # 下载逻辑故意保持流式写盘，避免把大文件整体读入内存。
    validate_remote_source_url(url)
    parsed = urlparse(url)
    filename = Path(parsed.path).name or "downloaded-skill"
    download_path = root_dir / filename
    timeout = httpx.Timeout(config.inputs.download_timeout_seconds)
    max_bytes = config.inputs.max_archive_size_mb * 1024 * 1024
    with httpx.Client(timeout=timeout, follow_redirects=False) as client:
        current_url = url
        for redirect_index in range(config.inputs.max_redirects + 1):
            with client.stream("GET", current_url) as response:
                if response.is_redirect:
                    location = response.headers.get("location")
                    if not location:
                        raise validation_error("invalid_remote_redirect", "Remote URL returned a redirect without location.")
                    if redirect_index >= config.inputs.max_redirects:
                        raise validation_error(
                            "too_many_redirects",
                            f"Remote URL exceeded redirect limit: {config.inputs.max_redirects}.",
                            max_redirects=config.inputs.max_redirects,
                        )
                    next_url = urljoin(current_url, location)
                    validate_remote_source_url(next_url)
                    current_url = next_url
                    continue
                response.raise_for_status()
                header_size = response.headers.get("content-length")
                if header_size is not None:
                    try:
                        if int(header_size) > max_bytes:
                            raise validation_error(
                                "remote_too_large",
                                f"Remote input is too large: {int(header_size)} bytes > {max_bytes} bytes.",
                                remote_size=int(header_size),
                                max_archive_size_bytes=max_bytes,
                            )
                    except ValueError:
                        pass
                with download_path.open("wb") as f:
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > max_bytes:
                            raise validation_error(
                                "remote_too_large",
                                f"Remote input is too large: {total} bytes > {max_bytes} bytes.",
                                remote_size=total,
                                max_archive_size_bytes=max_bytes,
                            )
                        f.write(chunk)
                return download_path
        raise validation_error(
            "too_many_redirects",
            f"Remote URL exceeded redirect limit: {config.inputs.max_redirects}.",
            max_redirects=config.inputs.max_redirects,
        )
    return download_path


def _clone_repo(url: str, dst: Path) -> None:
    # 使用 shallow clone，降低网络和磁盘成本；当前扫描只关注当前仓库快照。
    shutil.rmtree(dst, ignore_errors=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    import subprocess

    subprocess.run(["git", "clone", "--depth", "1", url, str(dst)], check=True, capture_output=True, text=True)


def _stage_single_file(path: Path, dst: Path) -> None:
    # 对非压缩包 URL，统一放入 normalized 根目录，保持后续检测器的遍历入口一致。
    name = path.name or "downloaded-skill"
    shutil.copy2(path, dst / name)


def _validate_local_archive_size(path: Path, config: SkillLintConfig) -> None:
    max_bytes = config.inputs.max_archive_size_mb * 1024 * 1024
    try:
        size = path.stat().st_size
    except OSError as exc:  # pragma: no cover
        raise validation_error("archive_inspection_failed", f"Unable to inspect archive: {path}") from exc
    if size > max_bytes:
        raise validation_error(
            "archive_too_large",
            f"Archive is too large: {size} bytes > {max_bytes} bytes.",
            archive_size=size,
            max_archive_size_bytes=max_bytes,
        )
