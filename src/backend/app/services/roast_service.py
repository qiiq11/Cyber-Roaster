"""评审服务：编排 LLM 调用、结果落库与查询。"""

from __future__ import annotations

import ast
import builtins
import hashlib
import json
import keyword
import logging
import re
from typing import Any, Dict, List, Optional

import javalang

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

# 需要硬编码过滤的内置类型与 typing 模块常用名称（双重保险，
# 防止类型注解如 List[float] 中的 List 被误认为用户变量）。
BUILTIN_TYPES = frozenset(
    {
        "List",
        "Dict",
        "Set",
        "Tuple",
        "Optional",
        "Union",
        "Any",
        "Callable",
        "TypeVar",
        "Generic",
        "Iterable",
        "Iterator",
        "Sequence",
        "Mapping",
        "MutableSequence",
        "MutableMapping",
        "str",
        "int",
        "float",
        "bool",
        "bytes",
        "bytearray",
        "object",
        "type",
        "None",
        "True",
        "False",
        "Ellipsis",
        "Exception",
        "ValueError",
        "TypeError",
        "IndexError",
        "KeyError",
    }
)

# 解析失败时的占位提示，避免返回空列表导致 AI 编造变量名。
_UNRECOGNIZED_VAR = "（无法识别变量名）"

# Java 关键字，用于正则回退时过滤
_JAVA_KEYWORDS = frozenset(
    {
        "abstract",
        "assert",
        "boolean",
        "break",
        "byte",
        "case",
        "catch",
        "char",
        "class",
        "const",
        "continue",
        "default",
        "do",
        "double",
        "else",
        "enum",
        "extends",
        "final",
        "finally",
        "float",
        "for",
        "goto",
        "if",
        "implements",
        "import",
        "instanceof",
        "int",
        "interface",
        "long",
        "native",
        "new",
        "package",
        "private",
        "protected",
        "public",
        "return",
        "short",
        "static",
        "strictfp",
        "super",
        "switch",
        "synchronized",
        "this",
        "throw",
        "throws",
        "transient",
        "try",
        "void",
        "volatile",
        "while",
    }
)

# 用于正则回退提取的语言集合（未实现 AST 解析的语言）
_REGEX_LANGUAGES = frozenset(
    {
        "javascript",
        "js",
        "typescript",
        "ts",
        "cpp",
        "c++",
        "c",
        "go",
        "rust",
        "rs",
        "java",
        "text",
    }
)

# 顶层函数/类名正则（跨语言通用，用于未实现 AST 解析时的回退）
_FUNC_RE = re.compile(
    r"\b(?:func|fn|function|def|void|int|bool|boolean|string|String|char|float|"
    r"double)\s+([A-Za-z_]\w*)\s*\("
)
_CLASS_RE = re.compile(r"\b(?:class|struct|interface|type)\s+([A-Za-z_]\w*)")


def _regex_extract_variables(code: str, language: str) -> Dict[str, Any]:
    """对未实现 AST 解析的语言，用正则回退提取顶层函数/类名。

    返回非空的 variables，避免 AI 因空列表而编造变量名。
    """
    names: set = set()
    for m in _FUNC_RE.finditer(code):
        names.add(m.group(1))
    for m in _CLASS_RE.finditer(code):
        names.add(m.group(1))

    # 过滤关键字与常见类型名
    filtered = [n for n in names if n not in _JAVA_KEYWORDS and n not in BUILTIN_TYPES]

    variables = sorted(filtered) if filtered else [_UNRECOGNIZED_VAR]
    return {"max_nesting_depth": 0, "variables": variables}


def _analyze_python(code: str) -> Dict[str, Any]:
    """用 Python AST 提取最大嵌套深度与变量名列表。"""
    try:
        tree = ast.parse(code)
    except (SyntaxError, ValueError):
        return {"max_nesting_depth": 0, "variables": [_UNRECOGNIZED_VAR]}

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

    collector = VariableCollector()
    collector.visit(tree)

    variables: List[str] = sorted(
        v
        for v in collector.variables
        if v not in keyword.kwlist
        and v not in _NON_VARIABLE_NAMES
        and v not in BUILTIN_TYPES
    )

    if not variables:
        variables = [_UNRECOGNIZED_VAR]

    return {"max_nesting_depth": visitor.max, "variables": variables}


def _analyze_java(code: str) -> Dict[str, Any]:
    """用 javalang 解析 Java 代码，提取类名、方法名、参数名、字段名与嵌套深度。"""
    try:
        tree = javalang.parse.parse(code)
    except Exception:  # noqa: BLE001 - javalang 解析失败时回退正则
        return _regex_extract_variables(code, "java")

    class_names: set = set()
    method_names: set = set()
    var_names: set = set()

    # Java 中会引入新嵌套层级的语句节点
    nesting_types = (
        javalang.tree.IfStatement,
        javalang.tree.ForStatement,
        javalang.tree.WhileStatement,
        javalang.tree.DoStatement,
        javalang.tree.TryStatement,
        javalang.tree.SwitchStatement,
    )

    max_nesting_depth = 0
    for path, node in tree:
        if isinstance(node, javalang.tree.ClassDeclaration):
            class_names.add(node.name)
        elif isinstance(node, javalang.tree.MethodDeclaration):
            method_names.add(node.name)
            for param in node.parameters:
                var_names.add(param.name)
        elif isinstance(node, javalang.tree.ConstructorDeclaration):
            for param in node.parameters:
                var_names.add(param.name)
        elif isinstance(node, javalang.tree.VariableDeclarator):
            var_names.add(node.name)
        elif isinstance(node, javalang.tree.FormalParameter):
            var_names.add(node.name)

        # 计算嵌套深度：对每个节点统计其祖先链（path）中嵌套语句的数量。
        # 注意要对「所有节点」而非仅嵌套语句节点计算，因为 path 不含节点
        # 自身——真正的最大深度出现在最内层的叶子节点上（其 path 含全部
        # 外层嵌套语句）。
        depth = sum(1 for p in path if isinstance(p, nesting_types))
        max_nesting_depth = max(max_nesting_depth, depth)

    variables = sorted(class_names | method_names | var_names)
    variables = [
        v for v in variables if v not in _JAVA_KEYWORDS and v not in BUILTIN_TYPES
    ]

    if not variables:
        variables = [_UNRECOGNIZED_VAR]

    return {"max_nesting_depth": max_nesting_depth, "variables": variables}


class VariableCollector(ast.NodeVisitor):
    """精确收集「用户定义/赋值」的变量名，排除类型注解引用。

    通过判断 ``ast.Name.ctx`` 是否为 ``ast.Store``，只捕获作为赋值目标
    出现的名称；类型注解（如 ``List[float]`` 中的 ``List``）是 ``Load``
    上下文，不会被误抓。函数/类名、函数参数单独处理。
    """

    def __init__(self) -> None:
        self.variables: set = set()

    def visit_Name(self, node: ast.Name) -> None:
        # 只收集作为赋值目标的变量（ctx=Store）
        if isinstance(node.ctx, ast.Store):
            self.variables.add(node.id)
        self.generic_visit(node)

    def visit_arg(self, node: ast.arg) -> None:
        # 收集函数参数名（参数是 ast.arg，不是 Name 节点）
        self.variables.add(node.arg)
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # 收集函数名本身
        self.variables.add(node.name)
        self.generic_visit(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self.variables.add(node.name)
        self.generic_visit(node)

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        # 收集类名本身
        self.variables.add(node.name)
        self.generic_visit(node)

    def visit_Assign(self, node: ast.Assign) -> None:
        # 显式收集赋值 targets 中的名称（与 visit_Name 的 Store 判断互补兜底）
        for target in node.targets:
            if isinstance(target, ast.Name):
                self.variables.add(target.id)
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        # 带类型注解的赋值（如 x: int = 5）
        if isinstance(node.target, ast.Name):
            self.variables.add(node.target.id)
        self.generic_visit(node)


def analyze_code_structure(code: str, language: str = "python") -> Dict[str, Any]:
    """按语言分流解析代码，提取最大嵌套深度与变量名列表。

    该结果作为「代码事实锚点」注入 LLM Prompt，用于对抗 AI 评审幻觉：
    - ``max_nesting_depth``：最大嵌套深度（Python 精确计算，其他语言回退为 0）。
    - ``variables``：真实的用户变量/类名/方法名/参数名列表。

    分流规则：
    - python → ast 精确解析。
    - java → javalang 解析（类名/方法名/参数名/字段名）。
    - 其他语言（javascript/cpp 等）→ 正则回退提取顶层函数/类名。

    任何情况下都不会返回空列表：解析失败时返回占位提示
    ``（无法识别变量名）``，避免 AI 因空列表而编造变量名。
    """
    lang = language.lower()

    if lang in ("python", "py"):
        return _analyze_python(code)

    if lang == "java":
        return _analyze_java(code)

    # 其他语言：正则回退
    return _regex_extract_variables(code, lang)


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
