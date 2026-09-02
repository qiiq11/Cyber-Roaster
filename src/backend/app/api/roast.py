"""评审相关 API 路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.models.database import get_db
from app.models.schemas import RoastRequest, RoastResponse
from app.services import roast_service
from app.services.roast_service import RoastService, analysis_to_dict

router = APIRouter(prefix="/roast", tags=["roast"])


@router.post("", response_model=RoastResponse, summary="对代码片段进行幽默评审")
async def roast_code(
    payload: RoastRequest,
    db: Session = Depends(get_db),
) -> RoastResponse:
    """调用 LLM 生成幽默评语，并持久化评审记录。"""
    service = RoastService(db)
    record = await service.roast(payload)
    return RoastResponse(**analysis_to_dict(record))


@router.get("/{analysis_id}", response_model=RoastResponse, summary="查询单次评审记录")
def get_roast(
    analysis_id: int,
    db: Session = Depends(get_db),
) -> RoastResponse:
    record = roast_service.RoastService(db).get(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="未找到该评审记录")
    return RoastResponse(**analysis_to_dict(record))
