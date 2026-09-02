"""pytest-bdd 步骤定义：与 roast.feature 一一对应。

通过共享 fixture `ctx` 在步骤间传递 payload 与响应，避免字符串判断场景名。
"""

from __future__ import annotations

from pathlib import Path

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

# 使用绝对路径加载 feature 文件，避免相对路径解析到 steps 目录
_FEATURE_DIR = Path(__file__).resolve().parents[1] / "features"
scenarios(str(_FEATURE_DIR / "roast.feature"))


@pytest.fixture
def ctx():
    """步骤间共享上下文。"""
    return {}


@given("我提交了一段合法的 Python 代码")
def given_valid_code(ctx):
    ctx["payload"] = {"code": "def foo():\n    return 42\n", "language": "python"}


@given("我提交一段空代码")
def given_empty_code(ctx):
    ctx["payload"] = {"code": "", "language": "python"}


@when("我调用评审接口")
def when_roast(client, ctx):
    ctx["roast_response"] = client.post("/roast", json=ctx["payload"])


@when("我调用统计接口")
def when_stats(client, ctx):
    ctx["stats_response"] = client.get("/stats")


@then("接口返回 200 状态码")
def then_200(ctx):
    assert ctx["roast_response"].status_code == 200


@then("接口返回 422 状态码")
def then_422(ctx):
    assert ctx["roast_response"].status_code == 422


@then("响应包含 roast_text 字段")
def then_has_roast_text(ctx):
    assert ctx["roast_response"].json()["roast_text"]


@then("响应包含 chaos_score 字段")
def then_has_chaos_score(ctx):
    assert "chaos_score" in ctx["roast_response"].json()


@then("chaos_score 在 0 到 100 之间")
def then_chaos_range(ctx):
    score = ctx["roast_response"].json()["chaos_score"]
    assert 0 <= score <= 100


@then(parsers.parse("统计接口返回 total_analyses 为 {expected:d}"))
def then_total(ctx, expected: int):
    assert ctx["stats_response"].json()["total_analyses"] == expected
