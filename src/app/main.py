from __future__ import annotations

from pathlib import Path

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import router as api_router

STATIC_DIR = Path(__file__).parent / "static"


def create_app() -> FastAPI:
    # Web app 采用“静态前端 + REST API”一体进程，部署简单，后续也容易拆分。
    app = FastAPI(
        title="SkillLint Web App",
        version="0.2.1",
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
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)


if __name__ == "__main__":
    run()
