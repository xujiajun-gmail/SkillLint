from __future__ import annotations

from collections import Counter
from pathlib import Path

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
}


def detect_report_language(text: str) -> str:
    chinese_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    english_letters = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    if chinese_chars >= 6 and chinese_chars >= max(english_letters // 8, 1):
        return "zh"
    return "en"


def detect_language_from_paths(paths: list[Path], max_chars: int = 60000) -> str:
    chunks: list[str] = []
    total = 0
    for path in paths:
        if not path.is_file():
            continue
        if path.suffix.lower() not in TEXT_EXTENSIONS and path.name != "SKILL.md":
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not text:
            continue
        remaining = max_chars - total
        if remaining <= 0:
            break
        chunk = text[:remaining]
        chunks.append(chunk)
        total += len(chunk)
    return detect_report_language("\n".join(chunks))


def dominant_source_language(paths: list[Path]) -> str:
    scores = Counter()
    for path in paths:
        ext = path.suffix.lower()
        if ext in {".py", ".sh", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".swift", ".rb"}:
            scores[ext] += 1
    return scores.most_common(1)[0][0] if scores else "unknown"
