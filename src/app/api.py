from __future__ import annotations

import shutil
import tempfile
from pathlib import Path

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from app.schemas import AppScanResponse, HealthResponse, ScanOptions, URLScanRequest
from app.service import ScanService, parse_relative_paths

router = APIRouter()
service = ScanService()


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse()


@router.post("/scan/url", response_model=AppScanResponse)
def scan_url(payload: URLScanRequest) -> AppScanResponse:
    try:
        return service.scan_from_url(str(payload.url), ScanOptions.model_validate(payload.model_dump()))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/scan/archive", response_model=AppScanResponse)
async def scan_archive(
    file: UploadFile = File(...),
    language: str = Form("auto"),
    use_dataflow: bool = Form(True),
    use_llm: bool = Form(False),
) -> AppScanResponse:
    suffix = Path(file.filename or "skill.zip").suffix or ".zip"
    temp_dir = Path(tempfile.mkdtemp(prefix="skilllint-app-archive-"))
    archive_path = temp_dir / f"upload{suffix}"
    try:
        archive_path.write_bytes(await file.read())
        return service.scan_from_archive(
            archive_path,
            ScanOptions(
                language=language,
                use_dataflow=use_dataflow,
                use_llm=use_llm,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


@router.post("/scan/directory", response_model=AppScanResponse)
async def scan_directory(
    files: list[UploadFile] = File(...),
    relative_paths: str = Form(...),
    language: str = Form("auto"),
    use_dataflow: bool = Form(True),
    use_llm: bool = Form(False),
) -> AppScanResponse:
    temp_dir: Path | None = None
    try:
        rel_paths = parse_relative_paths(relative_paths)
        if len(rel_paths) != len(files):
            raise ValueError("relative_paths count must match uploaded files")
        uploaded = [(rel_path, await upload.read()) for rel_path, upload in zip(rel_paths, files, strict=True)]
        temp_dir = service.build_uploaded_directory(uploaded)
        return service.scan_from_directory(
            temp_dir,
            ScanOptions(
                language=language,
                use_dataflow=use_dataflow,
                use_llm=use_llm,
            ),
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    finally:
        if temp_dir is not None:
            shutil.rmtree(temp_dir, ignore_errors=True)
