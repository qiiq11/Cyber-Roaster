"""GitHub 集成相关 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.github_client import GitHubClient, GitHubClientError, get_github_client
from app.models.database import get_db
from app.models.schemas import (
    GitHubAnalyzeRequest,
    GitHubAnalyzeResponse,
    RoastRequest,
    RoastResponse,
)
from app.services.roast_service import RoastService, analysis_to_dict

router = APIRouter(prefix="/github", tags=["github"])


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

    # 将 Diff 文本作为代码上下文交给 LLM 评审
    roast_payload = RoastRequest(code=diff["diff_text"], language="diff")
    service = RoastService(db)
    record = await service.roast(roast_payload)
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
