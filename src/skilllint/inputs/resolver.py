from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from skilllint.models import TargetInfo

GIT_HOSTS = {"github.com", "gitlab.com"}


def resolve_target(target: str) -> TargetInfo:
    """把用户输入解析为统一的 TargetInfo。

    该层只做“类型识别”，不做下载、解压、clone；真正的物理准备由 workspace 层负责。
    """
    path = Path(target)
    if path.exists() and path.is_dir():
        return TargetInfo(raw=target, normalized_type="directory", resolved_path=str(path.resolve()))
    if path.exists() and path.is_file() and path.suffix.lower() == ".zip":
        return TargetInfo(raw=target, normalized_type="zip", resolved_path=str(path.resolve()))

    parsed = urlparse(target)
    if parsed.scheme in {"http", "https"}:
        # 这里不要求 URL 一定可达，只做语法层类型判断；真正网络失败会在 workspace 阶段暴露。
        if _looks_like_git_repo(parsed):
            return TargetInfo(raw=target, normalized_type="git", resolved_path=target)
        return TargetInfo(raw=target, normalized_type="url", resolved_path=target)

    return TargetInfo(raw=target, normalized_type="unknown", resolved_path=target)


def _looks_like_git_repo(parsed) -> bool:
    # 当前只做轻量启发式识别：命中常见 git host，且路径不像直接下载的压缩包。
    # 这样做的好处是无须发网络请求就能快速区分 git URL 与普通文件 URL。
    if parsed.netloc not in GIT_HOSTS:
        return False
    path_parts = [part for part in parsed.path.split("/") if part]
    if len(path_parts) < 2:
        return False
    return not parsed.path.endswith(('.zip', '.tar.gz', '.tgz'))
