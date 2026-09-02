"""Pydantic 数据契约模型。

定义 API 请求/响应结构与内部服务数据传递对象，
与 ORM 模型解耦，保证对外接口稳定。
"""

from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class RoastRequest(BaseModel):
    """POST /roast 请求体。"""

    code: str = Field(..., min_length=1, max_length=20000, description="待评审的代码片段")
    language: str = Field(default="python", max_length=32, description="编程语言")


class RoastResponse(BaseModel):
    """POST /roast 响应体。"""

    id: int
    roast_text: str
    chaos_score: int = Field(..., ge=0, le=100)
    suggestions: List[str]
    language: str
    code_length: int
    created_at: datetime


class StatsResponse(BaseModel):
    """GET /stats 响应体。"""

    total_analyses: int
    average_chaos_score: float
    max_chaos_score: int
    min_chaos_score: int
    total_commits: int
    total_memes: int


class GitHubAnalyzeRequest(BaseModel):
    """POST /github/analyze 请求体。"""

    repo: str = Field(..., min_length=3, max_length=200, description="仓库全名 owner/name")
    commit_sha: str = Field(..., min_length=6, max_length=64, description="提交 SHA")


class CommitFile(BaseModel):
    """提交中单个文件的变更统计。"""

    filename: str
    additions: int
    deletions: int
    language: str


class GitHubAnalyzeResponse(BaseModel):
    """POST /github/analyze 响应体。"""

    repo: str
    commit_sha: str
    total_additions: int
    total_deletions: int
    files: List[CommitFile]
    roast: RoastResponse


class MemeResponse(BaseModel):
    """POST /meme 响应体。"""

    id: int
    analysis_id: int
    png_url: str


class HealthResponse(BaseModel):
    """GET /health 响应体。"""

    status: str
    version: str
    llm_configured: bool
