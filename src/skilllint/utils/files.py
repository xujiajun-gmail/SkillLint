from __future__ import annotations

import os
from pathlib import Path

IGNORED_DIRS = {".git", "node_modules", "__pycache__", ".venv", "venv"}
TEXT_EXTENSIONS = {
    ".md",
    ".txt",
    ".yaml",
    ".yml",
    ".json",
    ".toml",
    ".ini",
    ".cfg",
    ".conf",
    ".py",
    ".sh",
    ".bash",
    ".zsh",
    ".js",
    ".ts",
    ".tsx",
    ".jsx",
    ".rb",
    ".go",
    ".java",
    ".swift",
    ".xml",
    ".html",
    ".css",
    ".sql",
}
BINARY_EXTENSIONS = {
    ".exe",
    ".dll",
    ".so",
    ".dylib",
    ".bin",
    ".jar",
    ".zip",
    ".tar",
    ".gz",
    ".7z",
    ".pdf",
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".woff",
    ".woff2",
    ".ttf",
    ".otf",
}


def iter_files(root: Path) -> list[Path]:
    # 统一文件遍历入口，顺便排除 node_modules/.git 等对扫描价值很低的目录。
    paths: list[Path] = []
    for current, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in IGNORED_DIRS]
        current_path = Path(current)
        for filename in filenames:
            paths.append(current_path / filename)
    return sorted(paths)


def is_probably_binary(path: Path) -> bool:
    # “后缀 + NUL 字节”双重判断，足够应对当前技能样本而不追求完全准确。
    if path.suffix.lower() in BINARY_EXTENSIONS:
        return True
    try:
        with path.open("rb") as f:
            sample = f.read(4096)
    except OSError:
        return False
    return b"\x00" in sample


def is_text_file(path: Path) -> bool:
    if path.name == "SKILL.md":
        return True
    if path.suffix.lower() in TEXT_EXTENSIONS:
        return True
    return not is_probably_binary(path)


def read_text(path: Path, max_chars: int = 200000) -> str:
    # 所有文本读取都做统一截断，避免单个超大文件拖垮扫描与 Web 响应。
    return path.read_text(encoding="utf-8", errors="ignore")[:max_chars]


def line_range_for_offset(text: str, start: int, end: int) -> tuple[int, int]:
    line_start = text.count("\n", 0, start) + 1
    line_end = text.count("\n", 0, end) + 1
    return line_start, max(line_start, line_end)


def extract_snippet(text: str, start_line: int, end_line: int, radius: int = 1) -> str:
    lines = text.splitlines()
    lo = max(0, start_line - 1 - radius)
    hi = min(len(lines), end_line + radius)
    return "\n".join(lines[lo:hi]).strip()
