"""LLM 调用封装。

基于 `openai` 库，通过 `base_url` 对接任意 OpenAI 兼容 API
（硅基流动 / Azure OpenAI / DeepSeek 等）。
当未配置 `OPENAI_API_KEY` 时，回退到本地确定性“幽默评语”生成器，
保证测试与演示环境无需外部依赖即可运行。
"""

from __future__ import annotations

import builtins
import hashlib
import json
import keyword
import logging
import random
from typing import Any, Dict, List, Optional

from openai import AsyncOpenAI

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# 本地回退评语模板：按 chaos_score 分桶，确保结果稳定且可复现。
_ROAST_TEMPLATES: List[str] = [
    "这段代码的缩进比我的咖啡还要混乱，变量名 `{var}` 简直是抽象艺术的巅峰。",
    "看到这行代码，编译器都忍不住想退休了。建议把 `{var}` 改得像个正常名字。",
    "你的函数长度已经超过了我的耐心阈值，能不能给后人留条活路？",
    "这层嵌套深得像马里亚纳海沟，`{var}` 在这里迷路了三次。",
    "空异常处理——勇敢！直接吞掉错误，假装一切安好。",
]

_SUGGESTION_TEMPLATES: List[str] = [
    "为变量使用更具描述性的命名，避免 `{var}` 这类缩写。",
    "将长函数拆分为多个职责单一的小函数。",
    "降低嵌套层级，考虑提前返回（early return）模式。",
    "为异常添加日志记录，而非静默吞掉。",
    "补充必要的类型注解与文档字符串。",
]


def _stable_random(seed: str) -> random.Random:
    """基于字符串种子生成可复现的随机数发生器。"""
    digest = int(hashlib.sha256(seed.encode("utf-8")).hexdigest()[:8], 16)
    return random.Random(digest)


def _pick_var(code: str, variables: Optional[List[str]] = None) -> str:
    """从代码中提取一个代表性 token 作为模板占位。

    优先使用 AST 提取的真实变量名（``variables``），避免误用关键字；
    仅在未提供变量列表时，才回退到分词，并排除 Python 关键字与内置名称。
    """
    if variables:
        return variables[0]
    for token in code.replace("\n", " ").split():
        if token.isidentifier() and len(token) >= 3:
            if token in keyword.kwlist or token in dir(builtins):
                continue
            return token
    return "result"


class LLMClient:
    """OpenAI 兼容 LLM 客户端封装。"""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._client: Optional[AsyncOpenAI] = None
        if self.settings.openai_api_key:
            self._client = AsyncOpenAI(
                api_key=self.settings.openai_api_key,
                base_url=self.settings.openai_base_url,
                timeout=self.settings.llm_timeout_seconds,
            )

    @property
    def available(self) -> bool:
        """是否配置了真实 LLM 端点。"""
        return self._client is not None

    async def generate_roast(
        self,
        code: str,
        language: str = "python",
        max_nesting_depth: int = 0,
        variables: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """对代码片段生成幽默评审。

        Args:
            code: 待评审的代码。
            language: 编程语言。
            max_nesting_depth: 由 AST 提取的真实最大嵌套深度（0 表示非 Python 或未解析）。
            variables: 由 AST 提取的真实用户变量名列表。

        Returns:
            包含 `roast_text`、`chaos_score`、`suggestions` 的字典。
        """
        if not self._client:
            return self._fallback_roast(code, max_nesting_depth, variables)

        # 硬性评分锚点：嵌套深度 ≤ 2 时，混乱度不得超过 20 分，
        # 防止 AI 对简单代码「幻觉式」给出虚高评分。
        variables_str = ", ".join(variables or []) or "（无用户变量）"

        # 语言感知提示：Java POJO 类需特殊引导，避免机械套用 Python 风格建议。
        language_hint = ""
        if (language or "").lower() == "java":
            language_hint = (
                "这段代码是 Java 语言，可能包含类定义、getter/setter 或 POJO 结构。"
                "请基于代码的实际复杂度评分，不要因为语言差异而给出极端分数。"
                "对 POJO 类（仅字段与 getter/setter）给出的建议应聚焦命名、封装性、"
                "可变性等实际问题，不要机械套用“补充类型注解”“拆分长函数”等"
                "Python 风格建议。\n"
            )

        system_prompt = (
            "你是一位尖酸刻薄但善意的代码评审机器人，风格幽默、赛博朋克。"
            "输出必须是严格 JSON，字段："
            '{"roast_text": "<幽默吐槽，中文>", '
            '"chaos_score": <0-100 整数，衡量代码混乱程度>, '
            '"suggestions": ["<可执行建议1>", "<建议2>", "<建议3>"]}'
            "\n\n【硬性评分锚点，必须严格遵守】\n"
            f"1. 系统已用 AST 静态解析该代码，真实的最大嵌套深度为 {max_nesting_depth} 层。"
            f"若最大嵌套深度 ≤ 2，则 chaos_score 必须 ≤ 20，不得给出更高分。\n"
            f"2. 系统已识别出真实的用户变量名列表为：{variables_str}。"
            "吐槽中提到的变量名必须来自该列表；"
            "严禁把 Python 关键字（如 import、def、for、class、return 等）"
            "或类型名称（如 List、Dict、Optional、Tuple、Union 等 typing 模块名称）"
            "当作用户变量来调侃。\n"
            "3. 评语必须紧扣代码的真实结构，不得凭空捏造不存在的嵌套或变量。\n"
            f"4. {language_hint}"
        )
        user_prompt = f"语言：{language}\n代码：\n{code}"

        try:
            resp = await self._client.chat.completions.create(
                model=self.settings.openai_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                temperature=self.settings.llm_temperature,
                max_tokens=self.settings.llm_max_tokens,
            )
            content = resp.choices[0].message.content or "{}"
            return self._parse_llm_json(content, code, max_nesting_depth, variables)
        except Exception as exc:  # noqa: BLE001 - 对外屏蔽底层错误，回退本地
            logger.warning("LLM 调用失败，回退本地生成器：%s", exc)
            return self._fallback_roast(code, max_nesting_depth, variables)

    @staticmethod
    def _parse_llm_json(
        content: str,
        code: str,
        max_nesting_depth: int = 0,
        variables: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """解析 LLM 返回的 JSON，失败则回退本地生成。"""
        try:
            # 剥离可能的 Markdown 代码块围栏
            text = content.strip()
            if text.startswith("```"):
                text = text.strip("`")
                if text.startswith("json"):
                    text = text[4:]
            data = json.loads(text)
            roast_text = str(data.get("roast_text", "")).strip()
            if not roast_text:
                raise ValueError("空 roast_text")
            chaos_score = int(data.get("chaos_score", 50))
            suggestions = data.get("suggestions", [])
            if not isinstance(suggestions, list) or not suggestions:
                suggestions = _SUGGESTION_TEMPLATES
            return {
                "roast_text": roast_text,
                "chaos_score": max(0, min(100, chaos_score)),
                "suggestions": [str(s) for s in suggestions][:5],
            }
        except (json.JSONDecodeError, ValueError, TypeError):
            return LLMClient._fallback_roast(code, max_nesting_depth, variables)

    @staticmethod
    def _fallback_roast(
        code: str,
        max_nesting_depth: int = 0,
        variables: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """确定性本地回退生成器（无 LLM 依赖），同样遵守 AST 反幻觉锚点。

        与真实 LLM 路径保持一致：优先使用 AST 提取的真实变量名，评分受
        「嵌套深度 ≤ 2 → chaos_score ≤ 20」硬性约束。
        """
        rng = _stable_random(code)
        var = _pick_var(code, variables)
        roast_text = rng.choice(_ROAST_TEMPLATES).format(var=var)

        # 硬性评分锚点：嵌套深度 ≤ 2 时，混乱度上限 20，与 Prompt 约定一致。
        # 注意：Java 无嵌套语句时 max_nesting_depth 为 0，也属于「简单代码」，
        # 应同样触发 ≤20 约束（用 <= 2 而非 `if max_nesting_depth and ...`）。
        if max_nesting_depth <= 2:
            chaos_score = rng.randint(5, 20)
        else:
            base = 40 + min(40, len(code) // 40) + code.count("\n") * 2
            chaos_score = max(5, min(95, base + rng.randint(0, 10)))

        suggestions = [s.format(var=var) for s in rng.sample(_SUGGESTION_TEMPLATES, 3)]
        return {
            "roast_text": roast_text,
            "chaos_score": chaos_score,
            "suggestions": suggestions,
        }


# 模块级单例，供服务层复用
_llm_client: Optional[LLMClient] = None


def get_llm_client() -> LLMClient:
    """返回全局 LLM 客户端单例。"""
    global _llm_client
    if _llm_client is None:
        _llm_client = LLMClient()
    return _llm_client
