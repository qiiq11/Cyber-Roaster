"""FastAPI 应用入口。

负责装配路由、CORS、限流、静态资源与生命周期钩子。
"""

from __future__ import annotations

import logging
import os
import sys
import threading
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api import github, meme, roast, stats, webhook
from app.core.config import get_settings
from app.core.llm import get_llm_client
from app.models.database import init_db
from app.models.schemas import HealthResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


def _frontend_dist_dir() -> Path:
    """定位前端构建产物目录。

    - 打包环境：PyInstaller 将 dist 解压到 sys._MEIPASS/frontend_dist。
    - 开发环境：src/frontend/dist。
    """
    if hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / "frontend_dist"
    # 开发环境：从 backend 目录向上两级到项目根，再定位前端 dist
    return Path(__file__).resolve().parents[3] / "src" / "frontend" / "dist"


def _open_browser_later(url: str, delay: float = 2.0) -> None:
    """延迟打开浏览器，避免阻塞服务启动。"""

    def _open() -> None:
        webbrowser.open(url)

    threading.Timer(delay, _open).start()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭钩子：初始化数据库。"""
    init_db()
    logger.info("数据库初始化完成")
    # 自动打开浏览器（打包后的 exe 双击体验）
    _open_browser_later("http://127.0.0.1:8000")
    yield


settings = get_settings()

# 确保静态资源目录存在（StaticFiles 在 mount 时即校验目录）
os.makedirs("./static/memes", exist_ok=True)

app = FastAPI(
    title="Cyber-Roaster",
    version=settings.app_version,
    description="基于 AI 的幽默代码评审与梗图生成工具",
    lifespan=lifespan,
    # 显式声明文档与 OpenAPI 路径，确保 Swagger UI 与 schema 始终可用
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# CORS：允许前端开发服务器跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(roast.router)
app.include_router(stats.router)
app.include_router(github.router)
app.include_router(webhook.router)
app.include_router(meme.router)

# 静态目录：用于托管生成的梗图 PNG
app.mount("/static", StaticFiles(directory="./static"), name="static")

# ---- 前端静态文件托管（必须放在 API 路由之后，避免拦截接口）----
_frontend_dist = _frontend_dist_dir()
if _frontend_dist.exists():
    app.mount(
        "/assets",
        StaticFiles(directory=str(_frontend_dist / "assets")),
        name="assets",
    )


@app.get("/", include_in_schema=False)
def serve_index() -> FileResponse:
    """返回前端首页。"""
    index = _frontend_dist / "index.html"
    if index.exists():
        return FileResponse(index)
    return {"message": "Cyber-Roaster API", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["meta"], summary="健康检查")
def health() -> HealthResponse:
    llm = get_llm_client()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        llm_configured=llm.available,
    )


@app.get("/{catchall:path}", include_in_schema=False)
def serve_spa(catchall: str) -> FileResponse:
    """SPA catch-all 路由。

    对非 API、非文档、非健康检查的 GET 请求，返回 index.html，
    以支持前端路由。注意：本路由位于所有 API 路由之后注册，
    FastAPI 按注册顺序匹配，因此不会拦截 /roast、/meme 等接口。
    """
    index = _frontend_dist / "index.html"
    if index.exists():
        return FileResponse(index)
    return FileResponse(_frontend_dist / "index.html")


if __name__ == "__main__":
    # 直接运行（含 PyInstaller 打包后的 exe）时，启动 uvicorn 服务
    import uvicorn

    uvicorn.run(app, host="127.0.0.1", port=8000, log_level="info")
