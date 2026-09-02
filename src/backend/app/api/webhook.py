"""GitHub Webhook 路由。

处理 Push 事件：校验签名 → 提取最新提交 SHA → 触发评审 → 持久化结果。
"""

from __future__ import annotations

import hashlib
import hmac
import logging

from fastapi import APIRouter, Depends, Header, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.github_client import get_github_client
from app.models.database import get_db
from app.models.schemas import RoastRequest
from app.services.roast_service import RoastService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhook", tags=["webhook"])


def _verify_signature(payload: bytes, signature: str, secret: str) -> bool:
    """校验 GitHub Webhook 的 HMAC-SHA256 签名。"""
    if not secret:
        return True  # 未配置 WEBHOOK_SECRET 时跳过校验（开发模式）
    digest = hmac.new(secret.encode("utf-8"), payload, hashlib.sha256).hexdigest()
    expected = f"sha256={digest}"
    return hmac.compare_digest(expected, signature)


@router.post("/github", summary="接收 GitHub Push 事件并自动触发评审")
async def github_webhook(
    request: Request,
    db: Session = Depends(get_db),
    x_hub_signature_256: str = Header(default=""),
) -> dict:
    settings = get_settings()
    payload = await request.body()

    if not _verify_signature(payload, x_hub_signature_256, settings.webhook_secret or ""):
        raise HTTPException(status_code=401, detail="Webhook 签名校验失败")

    try:
        data = await request.json()
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=400, detail="无效的 JSON 负载") from exc

    if data.get("zen") or data.get("hook_id"):
        # GitHub 发送的 ping 事件
        return {"status": "pong"}

    repo = (data.get("repository") or {}).get("full_name")
    commits = data.get("commits", [])
    head_sha = data.get("after")

    if not repo or not head_sha:
        raise HTTPException(status_code=400, detail="缺少 repo 或 after 字段")

    # 拉取最新提交 Diff 并评审
    client = get_github_client()
    diff = client.get_commit_diff(repo, head_sha)
    service = RoastService(db)
    record = await service.roast(RoastRequest(code=diff["diff_text"], language="diff"))
    service.attach_commit(
        analysis_id=record.id,
        repo=repo,
        commit_sha=head_sha,
        total_additions=diff["total_additions"],
        total_deletions=diff["total_deletions"],
    )

    return {
        "status": "ok",
        "analysis_id": record.id,
        "commits_received": len(commits),
    }
