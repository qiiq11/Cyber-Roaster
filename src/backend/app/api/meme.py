"""梗图生成相关 API 路由。"""

from __future__ import annotations

import os
import uuid

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.core.meme_generator import generate_meme_png
from app.models.database import Meme, get_db
from app.models.schemas import MemeResponse
from app.services.roast_service import RoastService, analysis_to_dict

router = APIRouter(prefix="/meme", tags=["meme"])

# PNG 输出目录
_OUTPUT_DIR = os.environ.get("MEME_OUTPUT_DIR", "./static/memes")


@router.post(
    "/{analysis_id}", response_model=MemeResponse, summary="基于评审结果生成四格漫画"
)
def generate_meme(
    analysis_id: int,
    db: Session = Depends(get_db),
) -> MemeResponse:
    record = RoastService(db).get(analysis_id)
    if record is None:
        raise HTTPException(status_code=404, detail="未找到该评审记录")

    analysis = analysis_to_dict(record)
    png_bytes = generate_meme_png(analysis)

    os.makedirs(_OUTPUT_DIR, exist_ok=True)
    filename = f"meme_{analysis_id}_{uuid.uuid4().hex[:8]}.png"
    png_path = os.path.join(_OUTPUT_DIR, filename)
    with open(png_path, "wb") as f:
        f.write(png_bytes)

    meme = Meme(analysis_id=analysis_id, png_path=png_path)
    db.add(meme)
    db.commit()
    db.refresh(meme)

    return MemeResponse(id=meme.id, analysis_id=analysis_id, png_url=f"/meme/{meme.id}")


@router.get("/{meme_id}", response_class=FileResponse, summary="下载梗图 PNG")
def get_meme(meme_id: int, db: Session = Depends(get_db)) -> FileResponse:
    meme = db.get(Meme, meme_id)
    if meme is None or not os.path.exists(meme.png_path):
        raise HTTPException(status_code=404, detail="梗图不存在")
    return FileResponse(meme.png_path, media_type="image/png", filename="roast.png")
