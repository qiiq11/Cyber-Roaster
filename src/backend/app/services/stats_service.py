"""统计服务：汇总评审、提交与梗图数据。"""

from __future__ import annotations

from typing import Any, Dict

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import AnalysisRecord, Commit, Meme


class StatsService:
    """统计分析业务逻辑。"""

    def __init__(self, db: Session):
        self.db = db

    def get_summary(self) -> Dict[str, Any]:
        total = self.db.query(func.count(AnalysisRecord.id)).scalar() or 0
        avg = (
            self.db.query(func.avg(AnalysisRecord.chaos_score)).scalar()
            if total > 0
            else 0.0
        )
        max_score = self.db.query(func.max(AnalysisRecord.chaos_score)).scalar() or 0
        min_score = (
            self.db.query(func.min(AnalysisRecord.chaos_score)).scalar() or 0
        )
        total_commits = self.db.query(func.count(Commit.id)).scalar() or 0
        total_memes = self.db.query(func.count(Meme.id)).scalar() or 0

        return {
            "total_analyses": int(total),
            "average_chaos_score": round(float(avg), 2),
            "max_chaos_score": int(max_score),
            "min_chaos_score": int(min_score),
            "total_commits": int(total_commits),
            "total_memes": int(total_memes),
        }
