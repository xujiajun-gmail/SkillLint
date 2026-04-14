from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from skilllint.models import TargetInfo

GIT_HOSTS = {"github.com", "gitlab.com"}


def resolve_target(target: str) -> TargetInfo:
    path = Path(target)
    if path.exists() and path.is_dir():
        return TargetInfo(raw=target, normalized_type="directory", resolved_path=str(path.resolve()))
    if path.exists() and path.is_file() and path.suffix.lower() == ".zip":
        return TargetInfo(raw=target, normalized_type="zip", resolved_path=str(path.resolve()))

    parsed = urlparse(target)
    if parsed.scheme in {"http", "https"}:
        if _looks_like_git_repo(parsed):
            return TargetInfo(raw=target, normalized_type="git", resolved_path=target)
        return TargetInfo(raw=target, normalized_type="url", resolved_path=target)

    return TargetInfo(raw=target, normalized_type="unknown", resolved_path=target)


def _looks_like_git_repo(parsed) -> bool:
    if parsed.netloc not in GIT_HOSTS:
        return False
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 2:
        return False
    return not parsed.path.endswith(('.zip', '.tar.gz', '.tgz'))
