#!/usr/bin/env python3
"""
AI短剧素材生成器
生成动漫风格的角色和场景图片
"""

from PIL import Image, ImageDraw, ImageFont
import os
from pathlib import Path

def create_robot_avatar():
    """创建小智机器人形象"""
    # 创建400x500的机器人形象
    img = Image.new('RGB', (400, 500), color='#1a1a2e')
    draw = ImageDraw.Draw(img)
    
    # 身体（圆角矩形）
    body_color = '#667eea'
    draw.rounded_rectangle([50, 100, 350, 450], radius=30, fill=body_color)
    
    # 头部（圆形）
    head_color = '#764ba2'
    draw.ellipse([100, 20, 300, 220], fill=head_color)
    
    # 眼睛（发光效果）
    draw.ellipse([140, 80, 180, 120], fill='#00ff88')  # 左眼
    draw.ellipse([220, 80, 260, 120], fill='#00ff88')  # 右眼
    
    # 眼睛高光
    draw.ellipse([150, 85, 165, 100], fill='#ffffff')
    draw.ellipse([230, 85, 245, 100], fill='#ffffff')
    
    # 嘴巴（根据表情变化）
    draw.arc([160, 140, 240, 180], start=0, end=180, fill='#ffffff', width=3)
    
    # 天线
    draw.line([200, 20, 200, 0], fill='#667eea', width=4)
    draw.ellipse([190, -10, 210, 10], fill='#ff6b6b')
    
    return img

def create_scene_image(scene_type, text=""):
    """创建场景图片"""
    width, height = 1080, 1920  # 抖音竖屏尺寸
    
    if scene_type == "loss":
        # 亏损场景 - 红色背景
        img = Image.new('RGB', (width, height), color='#2d132c')
        draw = ImageDraw.Draw(img)
        
        # 股票下跌图表
        draw.line([(100, 800), (980, 800)], fill='#333', width=2)
        points = [(100, 600), (300, 650), (500, 700), (700, 900), (980, 1200)]
        draw.line(points, fill='#ff4444', width=8)
        
        # 文字
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 60)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        draw.text((width//2, 400), "-11%", fill='#ff4444', font=font_large, anchor='mm')
        draw.text((width//2, 550), "¥2,875", fill='#ff4444', font=font_large, anchor='mm')
        draw.text((width//2, 1400), "投资失败...", fill='#ffffff', font=font_small, anchor='mm')
        
    elif scene_type == "anger":
        # 愤怒场景 - 暗红背景
        img = Image.new('RGB', (width, height), color='#4a0e0e')
        draw = ImageDraw.Draw(img)
        
        # 愤怒符号
        draw.text((width//2, 600), "💢", fill='#ff4444', font=ImageFont.load_default(), anchor='mm')
        
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 80)
        except:
            font = ImageFont.load_default()
        
        draw.text((width//2, 1000), "你怎么搞的？！", fill='#ff6b6b', font=font, anchor='mm')
        draw.text((width//2, 1150), "天天亏钱！", fill='#ff6b6b', font=font, anchor='mm')
        
    elif scene_type == "idea":
        # 灵感场景 - 深蓝金背景
        img = Image.new('RGB', (width, height), color='#0f3460')
        draw = ImageDraw.Draw(img)
        
        # 灯泡效果
        center_x, center_y = width//2, 500
        
        # 发光圆环
        for r in range(200, 50, -10):
            alpha = int(255 * (200-r) / 150)
            color = (255, 215, 0, alpha)
            draw.ellipse([center_x-r, center_y-r, center_x+r, center_y+r], 
                        outline=(255, 215, 0), width=3)
        
        # 灯泡
        draw.ellipse([center_x-100, center_y-100, center_x+100, center_y+100], 
                    fill='#ffd700')
        
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 100)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        draw.text((width//2, 900), "💡 灵感！", fill='#ffd700', font=font_large, anchor='mm')
        draw.text((width//2, 1100), "充电桩市场！", fill='#ffffff', font=font_small, anchor='mm')
        
        # 数据卡片
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle([100, 1300, 980, 1450], radius=20, fill=(255, 255, 255, 50))
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        draw.text((width//2, 1375), "市场规模: 1000亿+", fill='#00ff88', font=font_small, anchor='mm')
        
    elif scene_type == "coding":
        # 编程场景 - 深色背景
        img = Image.new('RGB', (width, height), color='#1e1e1e')
        draw = ImageDraw.Draw(img)
        
        # 代码窗口
        draw.rounded_rectangle([50, 200, 1030, 1200], radius=20, fill='#2d2d2d')
        
        # 代码行
        try:
            font_code = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 40)
        except:
            font_code = ImageFont.load_default()
        
        code_lines = [
            ("class ChargeCloud:", '#569cd6'),
            ("    def __init__(self):", '#dcdcaa'),
            ("        self.product = '充电桩SaaS'", '#ce9178'),
            ("        self.docs = 12", '#b5cea8'),
            ("    def launch(self):", '#dcdcaa'),
            ("        return '产品完成！'", '#ffd700'),
        ]
        
        y = 300
        for line, color in code_lines:
            draw.text((100, y), line, fill=color, font=font_code)
            y += 80
        
        try:
            font_text = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 60)
        except:
            font_text = ImageFont.load_default()
        
        draw.text((width//2, 1400), "ChargeCloud诞生！", fill='#00ff88', font=font_text, anchor='mm')
        
    elif scene_type == "success":
        # 成功场景 - 绿色背景
        img = Image.new('RGB', (width, height), color='#1a5f1a')
        draw = ImageDraw.Draw(img)
        
        # 电话图标
        center_x, center_y = width//2, 500
        draw.ellipse([center_x-150, center_y-150, center_x+150, center_y+150], 
                    fill='#00ff88')
        
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 120)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 50)
        except:
            font_large = ImageFont.load_default()
            font_small = ImageFont.load_default()
        
        draw.text((width//2, 500), "📞", fill='#ffffff', font=font_large, anchor='mm')
        draw.text((width//2, 900), "第一单来了！", fill='#00ff88', font=font_large, anchor='mm')
        
        # CTA按钮
        draw.rounded_rectangle([200, 1300, 880, 1450], radius=30, fill='#667eea')
        draw.text((width//2, 1375), "关注小智 👉 AI创业日记", fill='#ffffff', font=font_small, anchor='mm')
    
    return img

def generate_all_assets():
    """生成所有素材"""
    output_dir = Path("/root/.openclaw/workspace/ai_agent/results/video_assets")
    output_dir.mkdir(parents=True, exist_ok=True)
    
    print("🎨 开始生成AI短剧素材...")
    
    # 生成机器人形象
    robot = create_robot_avatar()
    robot.save(output_dir / "robot_avatar.png")
    print(f"✅ 机器人形象: {output_dir}/robot_avatar.png")
    
    # 生成5个场景
    scenes = [
        ("loss", "亏损场景"),
        ("anger", "被骂场景"),
        ("idea", "灵感场景"),
        ("coding", "编程场景"),
        ("success", "成功场景"),
    ]
    
    for scene_type, desc in scenes:
        img = create_scene_image(scene_type)
        img.save(output_dir / f"scene_{scene_type}.png")
        print(f"✅ {desc}: {output_dir}/scene_{scene_type}.png")
    
    print(f"\n🎉 全部素材生成完成！保存在: {output_dir}")
    print(f"📊 总计: 1个角色 + 5个场景 = 6张图片")
    
    return output_dir

if __name__ == "__main__":
    generate_all_assets()
