"""梗图生成器。

主方案：调用免费第三方 memegen.link API（无需注册），将评审结果渲染为带文字的
表情包图片。每次从预设模板中随机选取一个。

备用方案：当 memegen.link 请求失败（网络异常、模板不存在等）时，自动降级回
Pillow 自绘四格漫画，保证功能不中断。
"""

from __future__ import annotations

import io
import logging
import random
import textwrap
import urllib.parse
from typing import Any, Dict, Optional

import httpx
from PIL import Image, ImageDraw, ImageFont

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# memegen.link 免费 API 基础地址
MEMEGEN_BASE_URL = "https://api.memegen.link"

# 预设表情包模板列表（均已在 memegen.link 上验证存在）。
# 说明：用户需求中的 trollface 在该 API 上不存在，已用同样契合「嘲讽代码」
# 主题的 spongebob（Mocking Spongebob）替代；disaster-girl / y-u-no 的
# 真实模板名为 disastergirl / yuno。
MEME_TEMPLATES = ["drake", "buzz", "disastergirl", "spongebob", "yuno"]

# 上下行文字长度上限（避免 URL 过长）
MAX_TOP_TEXT = 60
MAX_BOTTOM_TEXT = 40


def _truncate(text: str, max_len: int) -> str:
    """截断超长文本，末尾追加省略号。"""
    if len(text) <= max_len:
        return text
    return text[: max_len - 1] + "…"


def _encode_meme_text(text: str) -> str:
    """将文字编码为 memegen.link 接受的 URL 片段。

    memegen.link 约定：下划线 `_` 表示空格，波浪号 `~` 表示换行，
    其余字符做标准 URL 编码。
    """
    text = text.replace(" ", "_")
    text = text.replace("\n", "~")
    return urllib.parse.quote(text, safe="_~-")


def _fetch_memegen(
    template: str, top_text: str, bottom_text: str, timeout: float = 15.0
) -> Optional[bytes]:
    """调用 memegen.link 获取表情包 PNG 字节流。

    Args:
        template: 模板名（如 drake、buzz）。
        top_text: 上方文字。
        bottom_text: 下方文字。

    Returns:
        PNG 二进制内容；任何异常（网络错误 / 模板不存在 / 非 2xx）均返回 None。
    """
    top = _encode_meme_text(top_text)
    bottom = _encode_meme_text(bottom_text)
    url = f"{MEMEGEN_BASE_URL}/images/{template}/{top}/{bottom}.png"
    try:
        with httpx.Client(timeout=timeout, follow_redirects=True) as client:
            resp = client.get(url)
            resp.raise_for_status()
            return resp.content
    except httpx.HTTPError as exc:
        logger.warning("memegen.link 请求失败，将降级到 Pillow 自绘：%s", exc)
        return None


# ===== 备用方案：Pillow 自绘四格漫画 =====
# 画布尺寸：四格漫画，每格 400x300
PANEL_W, PANEL_H = 400, 300
COLS, ROWS = 2, 2
MARGIN = 20
CANVAS_W = MARGIN * 3 + PANEL_W * COLS
CANVAS_H = MARGIN * 3 + PANEL_H * ROWS

# 赛博朋克配色
BG_COLOR = (16, 16, 32)
PANEL_COLOR = (28, 22, 56)
BORDER_COLOR = (0, 229, 255)
TEXT_COLOR = (240, 240, 255)
ACCENT_COLOR = (255, 46, 136)
SCORE_COLOR = (255, 214, 0)


def _load_font(size: int) -> ImageFont.ImageFont:
    """尝试加载字体，失败则回退到 PIL 默认位图字体。"""
    for path in (
        "C:/Windows/Fonts/arial.ttf",
        "C:/Windows/Fonts/msyh.ttc",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default()


def _fit_text(draw: ImageDraw.ImageDraw, text: str, font, max_width: int) -> str:
    """按宽度将长文本折行，避免溢出气泡。"""
    return "\n".join(textwrap.wrap(text, width=max(8, max_width // 8)))


def _generate_meme_png_pillow(analysis: Dict[str, Any]) -> bytes:
    """备用方案：用 Pillow 自绘四格漫画 PNG。

    Args:
        analysis: 需含 `roast_text`、`chaos_score`、`suggestions` 字段。

    Returns:
        PNG 图片的二进制内容。
    """
    roast_text = str(analysis.get("roast_text", "无评语"))
    chaos_score = int(analysis.get("chaos_score", 0))
    suggestions = analysis.get("suggestions", []) or []
    suggestion_text = " ".join(str(s) for s in suggestions[:3])

    img = Image.new("RGB", (CANVAS_W, CANVAS_H), BG_COLOR)
    draw = ImageDraw.Draw(img)

    title_font = _load_font(30)
    body_font = _load_font(20)
    small_font = _load_font(16)

    # 标题
    title = "⚡ CODE ROASTER ⚡"
    draw.text((MARGIN, 10), title, fill=ACCENT_COLOR, font=title_font)

    panels = [
        ("第 1 格 · 案情陈述", "这段代码提交上来了\n评审机器人开始扫描……", None),
        ("第 2 格 · 评审毒舌", roast_text, None),
        ("第 3 格 · 混乱度评分", f"Chaos Score: {chaos_score} / 100", chaos_score),
        ("第 4 格 · 改进建议", suggestion_text, None),
    ]

    for idx, (header, body, score) in enumerate(panels):
        col, row = idx % COLS, idx // COLS
        x0 = MARGIN + col * (PANEL_W + MARGIN)
        y0 = MARGIN + 40 + row * (PANEL_H + MARGIN)
        x1, y1 = x0 + PANEL_W, y0 + PANEL_H

        # 面板底 + 霓虹边框
        draw.rectangle([x0, y0, x1, y1], fill=PANEL_COLOR)
        draw.rectangle([x0, y0, x1, y1], outline=BORDER_COLOR, width=3)

        # 面板标题
        draw.text((x0 + 12, y0 + 8), header, fill=ACCENT_COLOR, font=body_font)

        # 主体文字（折行）
        body_wrapped = _fit_text(draw, body, body_font, PANEL_W - 24)
        draw.multiline_text(
            (x0 + 12, y0 + 40),
            body_wrapped,
            fill=TEXT_COLOR,
            font=small_font,
            spacing=4,
        )

        # 评分条（仅评分格）
        if score is not None:
            bar_x0 = x0 + 12
            bar_y0 = y0 + PANEL_H - 40
            bar_w = PANEL_W - 24
            draw.rectangle(
                [bar_x0, bar_y0, bar_x0 + bar_w, bar_y0 + 14],
                outline=BORDER_COLOR,
                width=2,
            )
            fill_w = int(bar_w * score / 100)
            draw.rectangle(
                [bar_x0, bar_y0, bar_x0 + fill_w, bar_y0 + 14], fill=SCORE_COLOR
            )

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def generate_meme_png(analysis: Dict[str, Any]) -> bytes:
    """基于分析结果生成梗图 PNG（对外统一入口，接口保持不变）。

    主方案：调用 memegen.link 免费 API，将 ``roast_text`` 作为上排文字、
    ``chaos_score`` 作为下排文字填入随机模板。
    失败降级：自动回退到 Pillow 自绘四格漫画。

    Args:
        analysis: 需含 `roast_text`、`chaos_score`、`suggestions` 字段。

    Returns:
        PNG 图片的二进制内容。
    """
    settings = get_settings()
    roast_text = str(analysis.get("roast_text", "无评语"))
    chaos_score = int(analysis.get("chaos_score", 0))

    if settings.meme_template_preference.lower() == "memegen":
        template = random.choice(MEME_TEMPLATES)
        top_text = _truncate(roast_text, MAX_TOP_TEXT)
        bottom_text = f"Chaos Score: {chaos_score}/100"
        png = _fetch_memegen(template, top_text, bottom_text)
        if png is not None:
            return png
        logger.warning("memegen.link 不可用，降级到 Pillow 自绘方案")

    return _generate_meme_png_pillow(analysis)
