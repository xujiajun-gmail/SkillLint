from __future__ import annotations

import shutil
import zipfile
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from uuid import uuid4

import httpx

from skilllint.config import SkillLintConfig
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
        return iter_files(self.normalized_dir)

    def relpath(self, path: Path) -> str:
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
    normalized_dir = root_dir / "normalized"
    normalized_dir.mkdir(parents=True, exist_ok=True)

    extracted_from: str | None = None

    if target.normalized_type == "directory":
        _copy_directory(Path(target.resolved_path or target.raw), normalized_dir)
    elif target.normalized_type == "zip":
        extracted_from = str(Path(target.resolved_path or target.raw))
        _extract_zip(Path(target.resolved_path or target.raw), normalized_dir)
    elif target.normalized_type == "git":
        _clone_repo(target.resolved_path or target.raw, normalized_dir)
    elif target.normalized_type == "url":
        downloaded = _download_url(target.resolved_path or target.raw, root_dir, config)
        extracted_from = str(downloaded)
        if downloaded.suffix.lower() == ".zip":
            _extract_zip(downloaded, normalized_dir)
        else:
            _stage_single_file(downloaded, normalized_dir)
    else:
        raise ValueError(f"Unsupported target type: {target.normalized_type}")

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


def _extract_zip(zip_path: Path, dst: Path) -> None:
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(dst)


def _download_url(url: str, root_dir: Path, config: SkillLintConfig) -> Path:
    parsed = urlparse(url)
    filename = Path(parsed.path).name or "downloaded-skill"
    download_path = root_dir / filename
    timeout = httpx.Timeout(config.inputs.download_timeout_seconds)
    with httpx.stream("GET", url, timeout=timeout, follow_redirects=True) as response:
        response.raise_for_status()
        with download_path.open("wb") as f:
            for chunk in response.iter_bytes():
                f.write(chunk)
    return download_path


def _clone_repo(url: str, dst: Path) -> None:
    # 使用 shallow clone，降低网络和磁盘成本；当前扫描只关注当前仓库快照。
    shutil.rmtree(dst, ignore_errors=True)
    dst.parent.mkdir(parents=True, exist_ok=True)
    import subprocess

    subprocess.run(["git", "clone", "--depth", "1", url, str(dst)], check=True, capture_output=True, text=True)


def _stage_single_file(path: Path, dst: Path) -> None:
    name = path.name or "downloaded-skill"
    shutil.copy2(path, dst / name)
