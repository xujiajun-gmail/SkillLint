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
    # 报告语言判断采用极简启发式：
    # 中文字符足够多则输出中文，否则默认英文。
    chinese_chars = sum(1 for ch in text if "\u4e00" <= ch <= "\u9fff")
    english_letters = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    if chinese_chars >= 6 and chinese_chars >= max(english_letters // 8, 1):
        return "zh"
    return "en"


def detect_language_from_paths(paths: list[Path], max_chars: int = 60000) -> str:
    # 只抽样文本文件前 max_chars 个字符，避免为了语言检测去完整读取整个仓库。
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
    # 这里返回“主导源码后缀”，主要用于报告摘要，不做严格语言识别。
    scores = Counter()
    for path in paths:
        ext = path.suffix.lower()
        if ext in {".py", ".sh", ".js", ".ts", ".tsx", ".jsx", ".go", ".java", ".swift", ".rb"}:
            scores[ext] += 1
    return scores.most_common(1)[0][0] if scores else "unknown"
