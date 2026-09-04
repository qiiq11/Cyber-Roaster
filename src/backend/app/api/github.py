"""GitHub 集成相关 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from pydantic import ValidationError
from sqlalchemy.orm import Session

from app.core.github_client import GitHubClientError, get_github_client
from app.models.database import get_db
from app.models.schemas import (
    GitHubAnalyzeRequest,
    GitHubAnalyzeResponse,
    RoastRequest,
    RoastResponse,
)
from app.services.roast_service import RoastService, analysis_to_dict

router = APIRouter(prefix="/github", tags=["github"])

# 传给 LLM 的 Diff 文本最大长度。真实提交的 Diff 可能非常大（可达数百 KB），
# 远超 RoastRequest.code 的 20000 上限，且 LLM 也无需完整 Diff，
# 因此截断到安全长度，既避免触发校验失败导致 500，也控制 Token 成本。
_MAX_DIFF_CHARS = 18000


@router.post(
    "/analyze",
    response_model=GitHubAnalyzeResponse,
    summary="拉取提交 Diff 并分析评审",
)
async def analyze_github(
    payload: GitHubAnalyzeRequest,
    db: Session = Depends(get_db),
) -> GitHubAnalyzeResponse:
    client = get_github_client()
    try:
        diff = client.get_commit_diff(payload.repo, payload.commit_sha)
    except GitHubClientError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    # 将 Diff 文本截断后作为代码上下文交给 LLM 评审。
    # 注意：files 统计仍基于完整 diff 计算，此处仅截断用于 LLM 的文本。
    diff_text = diff["diff_text"][:_MAX_DIFF_CHARS]
    try:
        roast_payload = RoastRequest(code=diff_text, language="diff")
        service = RoastService(db)
        record = await service.roast(roast_payload)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=f"Diff 内容无效：{exc}") from exc

    service.attach_commit(
        analysis_id=record.id,
        repo=payload.repo,
        commit_sha=payload.commit_sha,
        total_additions=diff["total_additions"],
        total_deletions=diff["total_deletions"],
    )

    return GitHubAnalyzeResponse(
        repo=payload.repo,
        commit_sha=payload.commit_sha,
        total_additions=diff["total_additions"],
        total_deletions=diff["total_deletions"],
        files=diff["files"],
        roast=RoastResponse(**analysis_to_dict(record)),
    )
