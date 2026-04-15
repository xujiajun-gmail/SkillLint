from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, HttpUrl

from skilllint.models import ScanResult


class ScanOptions(BaseModel):
    """Web/API 层暴露给用户的最小扫描选项集。"""
    language: Literal["auto", "zh", "en"] = "auto"
    use_dataflow: bool = True
    use_llm: bool = False


class URLScanRequest(ScanOptions):
    url: HttpUrl


class SourceFileView(BaseModel):
    """供前端源码查看器使用的文件载荷。"""
    path: str
    content: str
    truncated: bool = False


class AppScanResponse(BaseModel):
    """Web API 的统一返回体。

    同时兼顾：
    - scan_result：给机器集成
    - report_markdown：给人类阅读/复制
    - source_files：给前端源码定位 UI
    """
    scan_result: ScanResult
    report_markdown: str
    source_files: dict[str, SourceFileView] = Field(default_factory=dict)


class HealthResponse(BaseModel):
    status: str = "ok"
