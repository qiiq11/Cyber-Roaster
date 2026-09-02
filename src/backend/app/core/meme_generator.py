"""梗图（四格漫画）生成器。

采用 Pillow 模板化方案（方案 A）：绘制固定四格漫画模板，
包含赛博朋克背景、角色头像、对话气泡与评分条，不调用任何图像生成 AI，
成本低、速度快、结果确定。将分析结果以文字形式嵌入画布并导出 PNG。
"""

from __future__ import annotations

import io
import textwrap
from typing import Any, Dict

from PIL import Image, ImageDraw, ImageFont

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


def generate_meme_png(analysis: Dict[str, Any]) -> bytes:
    """基于分析结果生成四格漫画 PNG 字节流。

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
            (x0 + 12, y0 + 40), body_wrapped, fill=TEXT_COLOR, font=small_font, spacing=4
        )

        # 评分条（仅评分格）
        if score is not None:
            bar_x0 = x0 + 12
            bar_y0 = y0 + PANEL_H - 40
            bar_w = PANEL_W - 24
            draw.rectangle([bar_x0, bar_y0, bar_x0 + bar_w, bar_y0 + 14],
                           outline=BORDER_COLOR, width=2)
            fill_w = int(bar_w * score / 100)
            draw.rectangle([bar_x0, bar_y0, bar_x0 + fill_w, bar_y0 + 14],
                           fill=SCORE_COLOR)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
