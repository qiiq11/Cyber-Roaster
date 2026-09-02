"""评审服务：编排 LLM 调用、结果落库与查询。"""

from __future__ import annotations

import ast
import builtins
import hashlib
import json
import keyword
import logging
from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.core.llm import get_llm_client
from app.models.database import AnalysisRecord, Commit
from app.models.schemas import RoastRequest

logger = logging.getLogger(__name__)


def _code_hash(code: str) -> str:
    return hashlib.sha256(code.encode("utf-8")).hexdigest()


# 会引入新嵌套层级的 AST 节点类型（函数/类/循环/条件/异常/上下文管理器）
_NESTING_NODES = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.ClassDef,
    ast.If,
    ast.For,
    ast.AsyncFor,
    ast.While,
    ast.Try,
    ast.With,
    ast.AsyncWith,
)

# 不作为「用户变量」展示的常量（Python 关键字由 keyword.kwlist 单独过滤）
_NON_VARIABLE_NAMES = frozenset({"True", "False", "None", "self", "cls"}) | frozenset(
    builtins.__dict__
)


def analyze_code_structure(code: str, language: str = "python") -> Dict[str, Any]:
    """用 AST 静态解析代码，提取真实的最大嵌套深度与变量名列表。

    该结果作为「代码事实锚点」注入 LLM Prompt，用于对抗 AI 评审幻觉：
    - ``max_nesting_depth``：真实的最大嵌套深度（函数/循环/条件等层级）。
    - ``variables``：真实的用户变量名列表（已排除 Python 关键字与内置常量）。

    非 Python 代码或语法错误时返回空结果，不阻断评审流程。
    """
    if language.lower() not in ("python", "py"):
        return {"max_nesting_depth": 0, "variables": []}

    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return {"max_nesting_depth": 0, "variables": []}

    class _NestingVisitor(ast.NodeVisitor):
        """递归统计最大嵌套深度。"""

        def __init__(self) -> None:
            self.current = 0
            self.max = 0

        def visit(self, node: ast.AST) -> None:  # type: ignore[override]
            if isinstance(node, _NESTING_NODES):
                self.current += 1
                self.max = max(self.max, self.current)
                self.generic_visit(node)
                self.current -= 1
            else:
                self.generic_visit(node)

    visitor = _NestingVisitor()
    visitor.visit(tree)

    variables: List[str] = sorted(
        {
            node.id
            for node in ast.walk(tree)
            if isinstance(node, ast.Name)
            and node.id not in keyword.kwlist
            and node.id not in _NON_VARIABLE_NAMES
        }
    )

    return {"max_nesting_depth": visitor.max, "variables": variables}


class RoastService:
    """代码评审业务逻辑。"""

    def __init__(self, db: Session):
        self.db = db
        self.llm = get_llm_client()

    async def roast(self, request: RoastRequest) -> AnalysisRecord:
        """执行评审并持久化记录。"""
        # 在调用 LLM 之前，先用 AST 提取真实的代码结构事实，
        # 作为「锚点」注入 Prompt，对抗评审幻觉。
        structure = analyze_code_structure(request.code, request.language)
        result = await self.llm.generate_roast(
            request.code,
            request.language,
            max_nesting_depth=structure["max_nesting_depth"],
            variables=structure["variables"],
        )

        record = AnalysisRecord(
            code_hash=_code_hash(request.code),
            language=request.language,
            code_length=len(request.code),
            roast_text=result["roast_text"],
            chaos_score=result["chaos_score"],
            suggestions=json.dumps(result["suggestions"], ensure_ascii=False),
            status="success",
        )
        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)
        return record

    def get(self, analysis_id: int) -> Optional[AnalysisRecord]:
        return self.db.get(AnalysisRecord, analysis_id)

    def attach_commit(
        self,
        analysis_id: int,
        repo: str,
        commit_sha: str,
        total_additions: int,
        total_deletions: int,
    ) -> Commit:
        """将 GitHub 提交关联到某次评审。"""
        commit = Commit(
            repo=repo,
            commit_sha=commit_sha,
            total_additions=total_additions,
            total_deletions=total_deletions,
            analysis_id=analysis_id,
        )
        self.db.add(commit)
        self.db.commit()
        self.db.refresh(commit)
        return commit


def analysis_to_dict(record: AnalysisRecord) -> Dict[str, Any]:
    """ORM 对象转 API 响应字典。"""
    try:
        suggestions = json.loads(record.suggestions)
    except (json.JSONDecodeError, TypeError):
        suggestions = []
    return {
        "id": record.id,
        "roast_text": record.roast_text,
        "chaos_score": record.chaos_score,
        "suggestions": suggestions,
        "language": record.language,
        "code_length": record.code_length,
        "created_at": record.created_at,
    }
