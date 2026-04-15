from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from skilllint.models import ScanResult


class ScanOptions(BaseModel):
    language: Literal["auto", "zh", "en"] = "auto"
    use_dataflow: bool = True
    use_llm: bool = False


class URLScanRequest(ScanOptions):
    url: HttpUrl


class SourceFileView(BaseModel):
    path: str
    content: str
    truncated: bool = False


class AppScanResponse(BaseModel):
    scan_result: ScanResult
    report_markdown: str
    source_files: dict[str, SourceFileView] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ok"
