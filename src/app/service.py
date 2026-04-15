from __future__ import annotations

import json
import shutil
import tempfile
from pathlib import Path

from app.schemas import AppScanResponse, ScanOptions, SourceFileView
from skilllint.config import SkillLintConfig, UnknownProfileError, load_config
from skilllint.core.scanner import SkillScanner
from skilllint.inputs.resolver import resolve_target
from skilllint.models import ScanResult
from skilllint.reporting.markdown_renderer import build_markdown
from skilllint.utils.files import is_text_file, read_text

SOURCE_FILE_CHAR_LIMIT = 200_000


class ScanService:
    """Web 层业务封装。

    API 层只负责收集 HTTP 请求；真正的扫描执行、工件收集与结果装配都放在 service 层，
    这样后续无论接 Web UI、别的后端服务还是任务队列，都可以复用同一套扫描逻辑。
    """

    def scan_from_url(self, url: str, options: ScanOptions) -> AppScanResponse:
        return self._scan_target(url, options)

    def scan_from_archive(self, archive_path: Path, options: ScanOptions) -> AppScanResponse:
        return self._scan_target(str(archive_path), options)

    def scan_from_directory(self, directory_path: Path, options: ScanOptions) -> AppScanResponse:
        return self._scan_target(str(directory_path), options)

    def build_uploaded_directory(self, files: list[tuple[str, bytes]]) -> Path:
        # 把浏览器上传的平铺文件列表重建成临时目录树，供现有扫描链路直接复用。
        temp_dir = Path(tempfile.mkdtemp(prefix="skilllint-app-dir-"))
        for relative_path, content in files:
            safe_path = self._safe_relative_path(relative_path)
            target = temp_dir / safe_path
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(content)
        return temp_dir

    def _scan_target(self, target: str, options: ScanOptions) -> AppScanResponse:
        cfg = self._build_scan_config(options)
        cfg.workspace.keep_artifacts = True

        resolved = resolve_target(target)
        if resolved.normalized_type == "unknown":
            raise ValueError(f"Unsupported scan target: {target}")

        scanner = SkillScanner(cfg)
        result = scanner.scan(resolved)

        source_files: dict[str, SourceFileView] = {}
        workspace_dir = Path(result.workspace.normalized_dir) if result.workspace else None
        if workspace_dir and workspace_dir.exists():
            # 只回传与 finding 相关的文本文件，避免把整个仓库源码都塞回前端。
            source_files = self._collect_source_files(result, workspace_dir)

        self._sanitize_workspace_for_response(result)
        report_markdown = build_markdown(result)

        if result.workspace:
            shutil.rmtree(Path(result.workspace.root_dir), ignore_errors=True)

        return AppScanResponse(
            scan_result=result,
            report_markdown=report_markdown,
            source_files=source_files,
        )

    def _build_scan_config(self, options: ScanOptions) -> SkillLintConfig:
        try:
            cfg = load_config()
        except UnknownProfileError as exc:
            raise ValueError(str(exc)) from exc
        cfg.outputs.report_language = options.language
        cfg.engines.dataflow.enabled = options.use_dataflow
        cfg.engines.semantic.use_llm = options.use_llm
        # Web 端刻意只暴露少量 scan 开关，不把完整 profile/rule filter 面暴露给普通用户。
        return cfg

    def _collect_source_files(self, result: ScanResult, workspace_dir: Path) -> dict[str, SourceFileView]:
        views: dict[str, SourceFileView] = {}
        target_files = sorted(
            {
                finding.evidence.file
                for finding in result.findings
                if finding.evidence.file
            }
        )
        for rel_path in target_files:
            path = workspace_dir / rel_path
            if not path.exists() or not path.is_file() or not is_text_file(path):
                continue
            content = read_text(path, max_chars=SOURCE_FILE_CHAR_LIMIT)
            truncated = path.stat().st_size > SOURCE_FILE_CHAR_LIMIT
            views[rel_path] = SourceFileView(
                path=rel_path,
                content=content,
                truncated=truncated,
            )
        return views

    @staticmethod
    def _sanitize_workspace_for_response(result: ScanResult) -> None:
        if result.workspace is None:
            return
        # Web API 的 workspace 只是临时工件，不应把服务端绝对路径暴露给前端或外部集成方。
        result.workspace.root_dir = "[ephemeral-web-workspace]"
        result.workspace.normalized_dir = "[ephemeral-web-workspace]/normalized"

    @staticmethod
    def _safe_relative_path(relative_path: str) -> Path:
        normalized = Path(relative_path.replace("\\", "/"))
        safe_parts = [part for part in normalized.parts if part not in {"", ".", ".."}]
        if not safe_parts:
            raise ValueError("Invalid uploaded path")
        return Path(*safe_parts)


def parse_relative_paths(raw: str) -> list[str]:
    # relative_paths 由前端以 JSON string array 形式传入，这里做统一解析与校验。
    data = json.loads(raw)
    if not isinstance(data, list) or not all(isinstance(item, str) for item in data):
        raise ValueError("relative_paths must be a JSON string array")
    return data
