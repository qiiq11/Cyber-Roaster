"""FastAPI 应用入口。

负责装配路由、CORS、限流、静态资源与生命周期钩子。
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用启动/关闭钩子：初始化数据库。"""
    init_db()
    logger.info("数据库初始化完成")
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


@app.get("/", tags=["meta"], summary="根路径")
def root() -> dict:
    return {"message": "Cyber-Roaster API", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["meta"], summary="健康检查")
def health() -> HealthResponse:
    llm = get_llm_client()
    return HealthResponse(
        status="ok",
        version=settings.app_version,
        llm_configured=llm.available,
    )
