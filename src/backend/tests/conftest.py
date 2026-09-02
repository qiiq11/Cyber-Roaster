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
os.environ.pop("OPENAI_API_KEY", None)  # 确保走本地回退生成器
os.environ.pop("GITHUB_TOKEN", None)    # 确保走模拟 Diff


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
