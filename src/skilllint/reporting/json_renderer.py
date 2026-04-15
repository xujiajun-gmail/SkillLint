from __future__ import annotations

from pathlib import Path

from skilllint.models import ScanResult


def render_json(result: ScanResult, path: str | Path) -> None:
    # JSON 直接输出完整 ScanResult，作为最稳定的机器可读格式。
    Path(path).write_text(result.model_dump_json(indent=2), encoding="utf-8")
