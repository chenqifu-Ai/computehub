#!/usr/bin/env python3
"""
AI短剧GIF动画生成器
使用PIL生成GIF动画（可直接作为短视频上传）
支持：帧动画、字幕、转场效果
"""

from PIL import Image, ImageDraw, ImageFont
from pathlib import Path
from datetime import datetime
import os

class GIFVideoGenerator:
    def __init__(self, output_dir="/root/.openclaw/workspace/ai_agent/results/video_assets"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
    def create_animated_gif(self):
        """生成带字幕的GIF动画"""
        print("🎬 开始生成GIF动画...")
        print("=" * 50)
        
        # 场景配置 (图片文件名, 显示帧数, 配音文字)
        scenes = [
            ("scene_loss.png", 45, "华联股份又跌了，亏了11%，两千多没了..."),
            ("scene_anger.png", 45, "老大骂我：你这个CEO怎么当的！天天亏钱！"),
            ("scene_idea.png", 45, "等等！新能源车充电市场！缺口300万个！"),
            ("scene_coding.png", 45, "ChargeCloud充电桩管理系统，搞定！"),
            ("scene_success.png", 60, "喂？张总，您的充电桩缺管理系统吗？第一单来了！"),
        ]
        
        frames = []
        fps = 15  # GIF帧率
        
        for idx, (img_file, frame_count, subtitle) in enumerate(scenes, 1):
            print(f"  📸 场景 {idx}/{len(scenes)}: {img_file}")
            
            img_path = self.output_dir / img_file
            if not img_path.exists():
                print(f"  ⚠️ 跳过: {img_path} 不存在")
                continue
            
            # 打开图片并添加字幕
            img = Image.open(img_path)
            img_with_sub = self.add_subtitle(img, subtitle)
            
            # 复制多帧（控制显示时长）
            for _ in range(frame_count):
                frames.append(img_with_sub)
            
            # 添加转场帧（黑场过渡）
            if idx < len(scenes):
                transition = self.create_transition_frame(img.size)
                for _ in range(5):  # 转场5帧
                    frames.append(transition)
        
        # 生成GIF
        output_gif = self.output_dir / "episode_01.gif"
        
        print(f"  🎞️ 生成GIF: {len(frames)}帧, {fps}fps")
        
        # 保存GIF
        frames[0].save(
            output_gif,
            save_all=True,
            append_images=frames[1:],
            duration=int(1000/fps),  # 每帧毫秒数
            loop=0,  # 无限循环
            optimize=True
        )
        
        # 同时生成MP4（如果环境支持）
        self.try_create_mp4(frames, fps)
        
        print(f"\n✅ GIF生成成功!")
        print(f"📁 文件位置: {output_gif}")
        print(f"📊 文件大小: {output_gif.stat().st_size / 1024:.1f} KB")
        
        # 生成报告
        self.generate_report(scenes, len(frames), fps)
        
        return output_gif
    
    def add_subtitle(self, img, text):
        """添加字幕到图片"""
        img = img.copy().convert('RGBA')
        width, height = img.size
        
        # 创建透明层
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay)
        
        # 字体
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 48)
            small_font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 36)
        except:
            font = ImageFont.load_default()
            small_font = ImageFont.load_default()
        
        # 字幕背景
        padding = 40
        line_height = 60
        
        # 计算文字换行
        lines = self.wrap_text(text, font, width - 200)
        total_height = len(lines) * line_height + padding * 2
        
        # 底部背景
        bg_y = height - total_height - 100
        draw.rounded_rectangle(
            [50, bg_y, width - 50, height - 50],
            radius=25,
            fill=(0, 0, 0, 200)
        )
        
        # 合并图层
        img = Image.alpha_composite(img, overlay)
        draw = ImageDraw.Draw(img)
        
        # 绘制文字
        y = bg_y + padding
        for line in lines:
            draw.text((width // 2, y), line, fill='#ffffff', font=font, anchor='mm')
            y += line_height
        
        return img.convert('RGB')
    
    def wrap_text(self, text, font, max_width):
        """文字自动换行"""
        words = text
        lines = []
        current_line = ""
        
        for char in words:
            test_line = current_line + char
            bbox = font.getbbox(test_line)
            if bbox[2] - bbox[0] <= max_width:
                current_line = test_line
            else:
                if current_line:
                    lines.append(current_line)
                current_line = char
        
        if current_line:
            lines.append(current_line)
        
        return lines if lines else [text]
    
    def create_transition_frame(self, size):
        """创建转场黑帧"""
        return Image.new('RGB', size, color='#000000')
    
    def try_create_mp4(self, frames, fps):
        """尝试生成MP4（使用imageio）"""
        try:
            import imageio
            output_mp4 = self.output_dir / "episode_01.mp4"
            
            print(f"  🎞️ 尝试生成MP4...")
            
            writer = imageio.get_writer(output_mp4, fps=fps)
            for frame in frames:
                writer.append_data(frame)
            writer.close()
            
            print(f"  ✅ MP4生成成功: {output_mp4}")
            return True
        except ImportError:
            print(f"  ℹ️ imageio未安装，仅生成GIF")
            return False
        except Exception as e:
            print(f"  ⚠️ MP4生成失败: {e}")
            return False
    
    def generate_report(self, scenes, total_frames, fps):
        """生成制作报告"""
        duration = total_frames / fps
        
        report = f"""
🎬 AI短剧制作完成报告
==================
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

📺 视频规格:
- 格式: GIF动画 (可转为MP4)
- 分辨率: 1080x1920 (抖音竖屏)
- 帧率: {fps}fps
- 总帧数: {total_frames}帧
- 总时长: {duration:.1f}秒

📝 场景列表:
"""
        for idx, (img, frames, subtitle) in enumerate(scenes, 1):
            scene_duration = frames / fps
            report += f"场景{idx}: {img} - {scene_duration:.1f}秒\n"
            report += f"  台词: {subtitle[:30]}...\n"
        
        report += f"""
✅ 输出文件:
- GIF: episode_01.gif
- MP4: episode_01.mp4 (如生成成功)

📱 使用说明:
1. GIF可直接上传到抖音/小红书
2. 或转为视频格式后上传
3. 建议添加BGM后发布

🎵 BGM推荐:
- 开头(0-3s): 紧张/低沉音乐
- 转折(6-9s): 轻快/希望音乐  
- 结尾(12-15s): 成功/激昂音乐
"""
        
        report_path = self.output_dir / "video_report.txt"
        with open(report_path, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"\n📄 报告已保存: {report_path}")
        print(report)

def main():
    print("=" * 60)
    print("🎬 AI短剧GIF视频生成器 v1.0")
    print("=" * 60)
    print()
    
    generator = GIFVideoGenerator()
    gif_path = generator.create_animated_gif()
    
    if gif_path and gif_path.exists():
        print("\n" + "=" * 60)
        print("🎉 视频制作完成！")
        print("=" * 60)
        print(f"\n📁 文件位置: {gif_path}")
        print(f"\n📧 准备打包发送邮件...")

if __name__ == "__main__":
    main()
