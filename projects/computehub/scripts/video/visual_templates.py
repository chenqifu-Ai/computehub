#!/usr/bin/env python3
"""
🎨 ComputeHub 视觉模板引擎
专业级视频渲染模板，支持渐变背景、装饰元素、排版系统

模板类型:
  - tech_blue:    科技蓝（默认，适合AI/技术类）
  - finance_gold: 金融金（适合金融/投资类）
  - nature_green: 自然绿（适合环保/农业类）
  - dark_elegant: 暗夜优雅（适合高端品牌）
  - minimal_white: 简约白（适合商务报告）
  - warm_orange:  暖橙（适合教育/生活类）
"""
from PIL import Image, ImageDraw, ImageFont, ImageFilter
import math
import os
import re


# ── 模板配置 ──────────────────────────────────────────────────

TEMPLATES = {
    "tech_blue": {
        "name": "科技蓝",
        "bg_top": (15, 30, 60),         # 顶部深蓝
        "bg_bottom": (25, 50, 100),     # 底部稍亮
        "accent": (59, 130, 246),       # 亮蓝
        "accent2": (147, 197, 253),     # 浅蓝
        "title_color": (255, 255, 255),
        "body_color": (226, 232, 240),
        "bullet_color": (147, 197, 253),
        "highlight_bg": (30, 64, 128),
        "deco_color": (59, 130, 246, 40),  # 装饰元素颜色（带透明度）
        "header_bar": True,
        "corner_deco": True,
        "footer_style": "line",
    },
    "finance_gold": {
        "name": "金融金",
        "bg_top": (20, 15, 5),
        "bg_bottom": (45, 35, 15),
        "accent": (218, 165, 32),       # 金色
        "accent2": (255, 215, 0),       # 亮金
        "title_color": (255, 215, 0),
        "body_color": (240, 235, 220),
        "bullet_color": (218, 165, 32),
        "highlight_bg": (60, 45, 15),
        "deco_color": (218, 165, 32, 30),
        "header_bar": True,
        "corner_deco": True,
        "footer_style": "line",
    },
    "nature_green": {
        "name": "自然绿",
        "bg_top": (10, 30, 15),
        "bg_bottom": (20, 60, 30),
        "accent": (34, 197, 94),        # 翠绿
        "accent2": (134, 239, 172),     # 浅绿
        "title_color": (255, 255, 255),
        "body_color": (220, 240, 225),
        "bullet_color": (134, 239, 172),
        "highlight_bg": (22, 101, 52),
        "deco_color": (34, 197, 94, 30),
        "header_bar": True,
        "corner_deco": True,
        "footer_style": "line",
    },
    "dark_elegant": {
        "name": "暗夜优雅",
        "bg_top": (10, 10, 18),
        "bg_bottom": (20, 20, 35),
        "accent": (139, 92, 246),       # 紫色
        "accent2": (196, 181, 253),     # 浅紫
        "title_color": (255, 255, 255),
        "body_color": (210, 210, 230),
        "bullet_color": (196, 181, 253),
        "highlight_bg": (46, 35, 80),
        "deco_color": (139, 92, 246, 30),
        "header_bar": True,
        "corner_deco": True,
        "footer_style": "line",
    },
    "minimal_white": {
        "name": "简约白",
        "bg_top": (245, 247, 250),
        "bg_bottom": (255, 255, 255),
        "accent": (37, 99, 235),        # 商务蓝
        "accent2": (96, 165, 250),
        "title_color": (30, 40, 60),
        "body_color": (60, 70, 90),
        "bullet_color": (37, 99, 235),
        "highlight_bg": (235, 240, 250),
        "deco_color": (37, 99, 235, 20),
        "header_bar": True,
        "corner_deco": False,
        "footer_style": "text",
    },
    "warm_orange": {
        "name": "暖橙",
        "bg_top": (50, 25, 10),
        "bg_bottom": (80, 45, 20),
        "accent": (249, 115, 22),       # 橙色
        "accent2": (251, 191, 36),      # 暖黄
        "title_color": (255, 255, 255),
        "body_color": (255, 240, 225),
        "bullet_color": (251, 191, 36),
        "highlight_bg": (90, 40, 18),
        "deco_color": (249, 115, 22, 30),
        "header_bar": True,
        "corner_deco": True,
        "footer_style": "line",
    },
    "ceremony_red": {
        "name": "庆典红",
        "bg_top": (60, 10, 10),
        "bg_bottom": (100, 25, 25),
        "accent": (220, 38, 38),        # 正红
        "accent2": (252, 165, 165),     # 浅红
        "title_color": (255, 255, 255),
        "body_color": (255, 220, 220),
        "bullet_color": (252, 165, 165),
        "highlight_bg": (100, 20, 20),
        "deco_color": (220, 38, 38, 35),
        "header_bar": True,
        "corner_deco": True,
        "footer_style": "line",
    },
}


# ── 渐变背景 ──────────────────────────────────────────────────

def draw_gradient(draw: ImageDraw.Draw, width: int, height: int,
                  top_color: tuple, bottom_color: tuple):
    """绘制垂直渐变背景"""
    for y in range(height):
        ratio = y / height
        r = int(top_color[0] * (1 - ratio) + bottom_color[0] * ratio)
        g = int(top_color[1] * (1 - ratio) + bottom_color[1] * ratio)
        b = int(top_color[2] * (1 - ratio) + bottom_color[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b))


def draw_radial_glow(draw: ImageDraw.Draw, width: int, height: int,
                     color: tuple, radius: int = 400):
    """在中心绘制径向光晕"""
    cx, cy = width // 2, height // 3
    for r in range(radius, 0, -1):
        alpha = int(15 * (1 - r / radius))
        if alpha <= 0:
            continue
        x0 = max(0, cx - r)
        y0 = max(0, cy - r)
        x1 = min(width, cx + r)
        y1 = min(height, cy + r)
        if x1 > x0 and y1 > y0:
            draw.ellipse([(x0, y0), (x1, y1)],
                         fill=(color[0], color[1], color[2], alpha))


def draw_corner_decoration(draw: ImageDraw.Draw, width: int, height: int,
                           color: tuple):
    """绘制角落装饰线"""
    size = 60
    # 左上角
    draw.line([(0, 0), (size, 0)], fill=color, width=3)
    draw.line([(0, 0), (0, size)], fill=color, width=3)
    # 右上角
    draw.line([(width - size, 0), (width, 0)], fill=color, width=3)
    draw.line([(width - 1, 0), (width - 1, size)], fill=color, width=3)
    # 左下角
    draw.line([(0, height - size), (0, height)], fill=color, width=3)
    draw.line([(0, height - 1), (size, height - 1)], fill=color, width=3)
    # 右下角
    draw.line([(width - size, height - 1), (width, height - 1)], fill=color, width=3)
    draw.line([(width - 1, height - size), (width - 1, height)], fill=color, width=3)


def draw_header_bar(draw: ImageDraw.Draw, width: int, accent_color: tuple):
    """绘制顶部装饰条"""
    bar_height = 4
    # 主色条
    draw.rectangle([(0, 0), (width, bar_height)], fill=accent_color)
    # 底部阴影
    for i in range(1, 4):
        draw.rectangle([(0, bar_height + i * 2), (width, bar_height + i * 2 + 1)],
                       fill=(accent_color[0], accent_color[1], accent_color[2], 30 - i * 8))


def draw_footer_line(draw: ImageDraw.Draw, width: int, height: int,
                     color: tuple):
    """绘制底部装饰线"""
    y = height - 50
    draw.line([(60, y), (width - 60, y)], fill=color, width=1)


def draw_page_number(draw: ImageDraw.Draw, width: int, height: int,
                     page_num: int, total: int, font, color="gray"):
    """绘制页码"""
    if total <= 1:
        return
    text = f"{page_num} / {total}"
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = width - tw - 40
    y = height - th - 20
    # 页码背景
    pad = 8
    draw.rounded_rectangle(
        [(x - pad, y - pad), (x + tw + pad, y + th + pad)],
        radius=10, fill=(0, 0, 0, 60)
    )
    draw.text((x, y), text, fill=color, font=font)


def draw_brand_watermark(draw: ImageDraw.Draw, width: int, height: int,
                         font, text="小智影业", color=(255, 255, 255, 30)):
    """绘制品牌水印"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    x = width - tw - 30
    y = height - th - 20
    draw.text((x, y), text, fill=color, font=font)


def draw_section_badge(draw: ImageDraw.Draw, x: int, y: int,
                       text: str, font, accent_color: tuple):
    """绘制章节标识（小圆角标签）"""
    bbox = draw.textbbox((0, 0), text, font=font)
    tw = bbox[2] - bbox[0]
    th = bbox[3] - bbox[1]
    pad_x, pad_y = 12, 4
    rx, ry = x - pad_x, y - pad_y
    rw, rh = tw + pad_x * 2, th + pad_y * 2
    draw.rounded_rectangle(
        [(rx, ry), (rx + rw, ry + rh)],
        radius=rh // 2, fill=accent_color
    )
    tx = x + (tw) // 2 - (bbox[2] - bbox[0]) // 2
    # 文字白色居中
    draw.text((x, y), text, fill="white", font=font)


# ── 智能排版 ──────────────────────────────────────────────────

def auto_wrap_text(draw, text: str, font, max_width: int) -> list:
    """自动换行，保持段落结构"""
    lines = []
    paragraphs = text.split("\n")
    for para in paragraphs:
        if not para.strip():
            lines.append("")
            continue
        chars = list(para)
        current = ""
        for ch in chars:
            test = current + ch
            bbox = draw.textbbox((0, 0), test, font=font)
            if (bbox[2] - bbox[0]) > max_width:
                lines.append(current)
                current = ch
            else:
                current = test
        if current:
            lines.append(current)
    return lines


def detect_bullet_items(text: str) -> list:
    """检测并拆分项目符号列表"""
    bullet_chars = ["•", "·", "-", "–", "—", "*", "●", "○", "◆", "▶"]
    items = []
    for line in text.split("\n"):
        stripped = line.strip()
        if not stripped:
            items.append(("empty", ""))
        elif any(stripped.startswith(b) for b in bullet_chars):
            items.append(("bullet", stripped.lstrip("•·-–—*●○◆▶ ")))
        elif re.match(r"^\d+[\.\)、]", stripped):
            items.append(("number", stripped))
        else:
            items.append(("text", stripped))
    return items


# ── 完整页面渲染 ──────────────────────────────────────────────

def render_page(
    page: dict,
    output_path: str,
    width: int = 1920,
    height: int = 1080,
    template: str = "tech_blue",
    font_path: str = None,
    show_brand: bool = True,
) -> str:
    """渲染单页为高清图片

    Args:
        page: doc_parser 输出的页数据 {"title", "text", "images", ...}
        output_path: 输出路径
        template: 模板名称
        font_path: 字体路径
        show_brand: 是否显示品牌水印

    Returns:
        输出路径
    """
    from PIL import Image, ImageDraw, ImageFont

    cfg = TEMPLATES.get(template, TEMPLATES["tech_blue"])

    # ── 创建画布 ──
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # ── 渐变背景 ──
    draw_gradient(draw, width, height, cfg["bg_top"], cfg["bg_bottom"])

    # ── 中心光晕 ──
    draw_radial_glow(draw, width, height, cfg["accent"], radius=350)

    # ── 顶部装饰条 ──
    if cfg.get("header_bar", True):
        draw_header_bar(draw, width, cfg["accent"])

    # ── 角落装饰 ──
    if cfg.get("corner_deco", True):
        draw_corner_decoration(draw, width, height, cfg["accent2"])

    # ── 加载字体 ──
    def load_font(size):
        if font_path and os.path.exists(font_path):
            try:
                return ImageFont.truetype(font_path, size)
            except Exception:
                pass
        try:
            return ImageFont.truetype("/system/fonts/DroidSans.ttf", size)
        except Exception:
            return ImageFont.load_default()

    font_title = load_font(52)
    font_body = load_font(34)
    font_small = load_font(24)
    font_brand = load_font(18)

    # ── 处理图片背景（如果有） ──
    has_full_image = False
    if page.get("images") and len(page["images"]) > 0:
        img_path = page["images"][0]
        if os.path.exists(img_path):
            try:
                bg_img = Image.open(img_path).convert("RGBA")
                # 铺满全屏（保持比例裁剪）
                bg_ratio = bg_img.width / bg_img.height
                target_ratio = width / height
                if bg_ratio > target_ratio:
                    new_h = height
                    new_w = int(height * bg_ratio)
                else:
                    new_w = width
                    new_h = int(width / bg_ratio)
                bg_img = bg_img.resize((new_w, new_h), Image.LANCZOS)
                # 居中裁剪
                left = (new_w - width) // 2
                top = (new_h - height) // 2
                bg_img = bg_img.crop((left, top, left + width, top + height))
                # 叠加暗色遮罩
                overlay = Image.new("RGBA", (width, height), (0, 0, 0, 140))
                bg_img = Image.alpha_composite(bg_img, overlay)
                img = bg_img
                draw = ImageDraw.Draw(img)
                has_full_image = True
            except Exception:
                pass

    # ── 标题 ──
    title = page.get("title", "")
    if title:
        # 标题区域背景
        if not has_full_image:
            title_bg_y = 30
            title_bg_h = 100
            draw.rectangle(
                [(0, title_bg_y), (width, title_bg_y + title_bg_h)],
                fill=(cfg["accent"][0], cfg["accent"][1], cfg["accent"][2], 30)
            )
            # 左侧竖线
            draw.rectangle(
                [(60, title_bg_y + 10), (64, title_bg_y + title_bg_h - 10)],
                fill=cfg["accent"]
            )

        # 标题文字居中
        title_y = 50
        bbox = draw.textbbox((0, 0), title, font=font_title)
        tw = bbox[2] - bbox[0]
        tx = (width - tw) // 2
        draw.text((tx, title_y), title, fill=cfg["title_color"], font=font_title)

        # 标题下划线装饰
        if not has_full_image:
            line_y = title_y + 80
            line_w = min(tw + 40, 600)
            line_x = (width - line_w) // 2
            draw.line([(line_x, line_y), (line_x + line_w, line_y)],
                      fill=cfg["accent2"], width=2)

    # ── 正文渲染 ──
    text = page.get("text", "")
    if text:
        # 检测是否为项目符号列表
        items = detect_bullet_items(text)

        margin_left = 100
        margin_right = 100
        content_width = width - margin_left - margin_right
        start_y = 160

        y = start_y
        line_height_body = 48
        bullet_indent = 40

        # 内容区域遮罩（深色半透明背景）
        if has_full_image:
            content_bottom = min(y + len(items) * (line_height_body + 8) + 40,
                                 height - 60)
            draw.rounded_rectangle(
                [(margin_left - 20, y - 10),
                 (width - margin_right + 20, content_bottom)],
                radius=16, fill=(0, 0, 0, 100)
            )

        for item_type, item_text in items:
            if item_type == "empty":
                y += line_height_body // 2
                continue

            lines = auto_wrap_text(draw, item_text, font_body, content_width - bullet_indent)

            for line in lines:
                if y > height - 100:
                    break

                if item_type == "bullet":
                    # 项目符号（圆点）
                    bullet_x = margin_left
                    dot_radius = 6
                    draw.ellipse(
                        [(bullet_x - dot_radius, y + line_height_body // 2 - dot_radius),
                         (bullet_x + dot_radius, y + line_height_body // 2 + dot_radius)],
                        fill=cfg["bullet_color"]
                    )
                    draw.text((margin_left + bullet_indent, y), line,
                              fill=cfg["body_color"], font=font_body)
                elif item_type == "number":
                    draw.text((margin_left, y), line,
                              fill=cfg["accent2"], font=font_body)
                else:
                    draw.text((margin_left, y), line,
                              fill=cfg["body_color"], font=font_body)

                y += line_height_body + 4

    # ── 页码 ──
    page_num = page.get("page_num", 1)
    total = page.get("total_pages", 1)
    draw_page_number(draw, width, height, page_num, total, font_small, color=cfg["accent2"])

    # ── 底部装饰线 ──
    if cfg.get("footer_style") == "line":
        draw_footer_line(draw, width, height, cfg["accent2"])

    # ── 品牌水印 ──
    if show_brand:
        draw_brand_watermark(draw, width, height, font_brand,
                             text="小智影业", color=(255, 255, 255, 40))

    # ── 保存 ──
    # 转 RGB（RGBA → RGB 用于 JPEG）
    if img.mode == "RGBA":
        bg = Image.new("RGB", (width, height), cfg["bg_top"])
        bg.paste(img, mask=img.split()[3])
        img = bg

    img.save(output_path, "JPEG", quality=92)
    return output_path


# ── 测试 ──────────────────────────────────────────────────────

def test_all_templates():
    """测试所有模板"""
    test_page = {
        "page_num": 1,
        "total_pages": 5,
        "title": "欢迎来到小智影业",
        "text": "• 专业的AI视频生成平台\n"
                "• 支持文档智能转视频\n"
                "• 多模板视觉风格\n\n"
                "我们的核心优势：\n"
                "1. 全自动管线流程\n"
                "2. 高清1080P输出\n"
                "3. 专业语音合成",
        "images": [],
        "has_image": False,
    }

    os.makedirs("/tmp/visual_test", exist_ok=True)
    for name in TEMPLATES:
        out = f"/tmp/visual_test/test_{name}.jpg"
        render_page(test_page, out, template=name)
        print(f"  ✅ {TEMPLATES[name]['name']} ({name}): {out}")


if __name__ == "__main__":
    print("🎨 视觉模板引擎测试")
    test_all_templates()
