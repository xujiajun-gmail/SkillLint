from __future__ import annotations

from pathlib import Path

from skilllint.models import ScanResult


def render_json(result: ScanResult, path: str | Path) -> None:
    Path(path).write_text(result.model_dump_json(indent=2), encoding="utf-8")
