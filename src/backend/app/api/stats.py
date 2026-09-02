"""统计相关 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas import StatsResponse
from app.services.stats_service import StatsService

router = APIRouter(prefix="/stats", tags=["stats"])


@router.get("", response_model=StatsResponse, summary="获取全局统计概览")
def get_stats(db: Session = Depends(get_db)) -> StatsResponse:
    return StatsResponse(**StatsService(db).get_summary())
