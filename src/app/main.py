from __future__ import annotations

import argparse
import os
from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router

STATIC_DIR = Path(__file__).parent / "static"
DEFAULT_WEB_HOST = "127.0.0.1"
DEFAULT_WEB_PORT = 18110


def create_app() -> FastAPI:
    # Web app 采用“静态前端 + REST API”一体进程，部署简单，后续也容易拆分。
    app = FastAPI(
        title="SkillLint Web App",
        version="0.2.2",
        docs_url="/api/docs",
        openapi_url="/api/openapi.json",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=False,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(api_router, prefix="/api")
    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    @app.get("/", include_in_schema=False)
    def index() -> FileResponse:
        # 根路径只返回静态首页，真正的数据请求全部走 /api。
        return FileResponse(STATIC_DIR / "index.html")

    return app


app = create_app()


def run() -> None:
    # skilllint-web 命令最终落到这里。
    # 启动参数优先级：
    # 1. CLI args
    # 2. env vars
    # 3. defaults
    parser = argparse.ArgumentParser(prog="skilllint-web", description="Run the SkillLint web app")
    parser.add_argument("--host", default=None, help=f"Bind host (default: env or {DEFAULT_WEB_HOST})")
    parser.add_argument("--port", type=int, default=None, help=f"Bind port (default: env or {DEFAULT_WEB_PORT})")
    args = parser.parse_args()

    env_host = os.getenv("SKILLLINT_WEB_HOST")
    env_port = os.getenv("SKILLLINT_WEB_PORT")

    host = args.host or env_host or DEFAULT_WEB_HOST
    port = args.port
    if port is None and env_port:
        try:
            port = int(env_port)
        except ValueError as exc:
            raise ValueError(f"Invalid SKILLLINT_WEB_PORT: {env_port}") from exc
    if port is None:
        port = DEFAULT_WEB_PORT
    if not (1 <= port <= 65535):
        raise ValueError(f"Invalid web port: {port}")

    uvicorn.run("app.main:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
