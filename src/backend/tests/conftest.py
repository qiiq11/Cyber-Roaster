"""pytest 全局 fixture。

提供隔离的内存数据库与测试客户端，避免污染开发环境数据。
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import pytest

# 将 backend 根目录加入 sys.path，确保 `app` 包可导入
BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

# 测试强制使用内存 SQLite，避免落盘
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
# 用空字符串覆盖（而非 pop），因为 get_settings() 会从 .env 文件读取配置，
# 环境变量的优先级高于 .env 文件，设为空值可确保测试走本地回退/mock 路径，
# 不依赖任何外部网络或真实密钥。
os.environ["OPENAI_API_KEY"] = ""
os.environ["GITHUB_TOKEN"] = ""
os.environ["MEME_TEMPLATE_PREFERENCE"] = "pillow"  # 测试走本地自绘，避免外部网络依赖


@pytest.fixture()
def client():
    """返回带 TestClient 的同步客户端（每次重新初始化内存库）。"""
    from fastapi.testclient import TestClient

    from app.main import app
    from app.models.database import Base, engine

    Base.metadata.create_all(bind=engine)
    with TestClient(app) as c:
        yield c
    Base.metadata.drop_all(bind=engine)
