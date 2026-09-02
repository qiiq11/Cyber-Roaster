"""SQLAlchemy ORM 模型与数据库会话。

- 开发环境使用 SQLite（`DATABASE_URL` 默认值）。
- 生产可切换 PostgreSQL，仅需更改 `DATABASE_URL`。
"""

from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    create_engine,
)
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

from app.core.config import get_settings

Base = declarative_base()


def _utcnow() -> datetime:
    """返回带 UTC 时区的当前时间。"""
    return datetime.now(timezone.utc)


class AnalysisRecord(Base):
    """一次代码评审记录。"""

    __tablename__ = "analyses"

    id = Column(Integer, primary_key=True, autoincrement=True)
    code_hash = Column(String(64), index=True, nullable=False)
    language = Column(String(32), nullable=False, default="python")
    code_length = Column(Integer, nullable=False)
    roast_text = Column(Text, nullable=False)
    chaos_score = Column(Integer, nullable=False)
    suggestions = Column(Text, nullable=False)  # JSON 数组序列化后的字符串
    status = Column(String(16), nullable=False, default="success")
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    commits = relationship("Commit", back_populates="analysis")
    memes = relationship("Meme", back_populates="analysis")


class Commit(Base):
    """GitHub 提交记录，关联一次评审。"""

    __tablename__ = "commits"

    id = Column(Integer, primary_key=True, autoincrement=True)
    repo = Column(String(200), nullable=False)
    commit_sha = Column(String(64), index=True, nullable=False)
    total_additions = Column(Integer, nullable=False, default=0)
    total_deletions = Column(Integer, nullable=False, default=0)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    analysis = relationship("AnalysisRecord", back_populates="commits")


class Meme(Base):
    """梗图生成记录，关联一次评审。"""

    __tablename__ = "memes"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(Integer, ForeignKey("analyses.id"), nullable=False)
    png_path = Column(String(500), nullable=False)
    created_at = Column(DateTime(timezone=True), default=_utcnow, nullable=False)

    analysis = relationship("AnalysisRecord", back_populates="memes")


# --- 引擎与会话工厂 ---
_settings = get_settings()
_connect_args = (
    {"check_same_thread": False} if _settings.database_url.startswith("sqlite") else {}
)
# 内存 SQLite 需使用 StaticPool，让所有连接共享同一份内存数据库，
# 否则 create_all 建的表在后续新连接中不可见。
_engine_kwargs: dict = {"future": True}
if _settings.database_url in ("sqlite://", "sqlite:///:memory:"):
    from sqlalchemy.pool import StaticPool

    _engine_kwargs["poolclass"] = StaticPool
engine = create_engine(
    _settings.database_url,
    connect_args=_connect_args,
    **_engine_kwargs,
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def init_db() -> None:
    """创建全部数据表（幂等）。"""
    Base.metadata.create_all(bind=engine)


def get_db():
    """FastAPI 依赖：提供数据库会话，请求结束后关闭。"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
