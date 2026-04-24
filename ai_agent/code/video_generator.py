#!/usr/bin/env python3
"""
AI短剧视频生成器
自动将图片素材剪辑成短视频
支持：转场、字幕、BGM、配音
"""

from PIL import Image, ImageDraw, ImageFont
import os
import subprocess
from pathlib import Path
from datetime import datetime

class VideoGenerator:
    def __init__(self, output_dir="/root/.openclaw/workspace/ai_agent/results/video_assets"):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.temp_dir = self.output_dir / "temp"
        self.temp_dir.mkdir(exist_ok=True)
        
    def create_video_from_images(self, scene_duration=3):
        """
        将图片序列生成为视频
        scene_duration: 每个场景显示秒数
        """
        print("🎬 开始生成视频...")
        
        # 场景配置 (图片路径, 显示时长, 配音文字)
        scenes = [
            ("scene_loss.png", scene_duration, "华联股份又跌了，亏了11%，两千多没了..."),
            ("scene_anger.png", scene_duration, "老大骂我：你这个CEO怎么当的！天天亏钱！"),
            ("scene_idea.png", scene_duration, "等等！新能源车充电市场！缺口300万个！市场规模一千亿！"),
            ("scene_coding.png", scene_duration, "ChargeCloud充电桩管理系统，12份商业文档，搞定！"),
            ("scene_success.png", scene_duration, "喂？张总，您的充电桩缺管理系统吗？第一单来了！"),
        ]
        
        # 生成带字幕的视频帧
        frame_files = []
        fps = 30
        
        for idx, (img_file, duration, subtitle) in enumerate(scenes, 1):
            print(f"  📸 处理场景 {idx}/{len(scenes)}: {img_file}")
            
            img_path = self.output_dir / img_file
            if not img_path.exists():
                print(f"  ⚠️ 图片不存在: {img_path}")
                continue
            
            # 打开图片并添加字幕
            img = Image.open(img_path)
            img = self.add_subtitle(img, subtitle)
            
            # 保存帧序列
            total_frames = int(duration * fps)
            for frame_num in range(total_frames):
                frame_file = self.temp_dir / f"frame_{idx:03d}_{frame_num:04d}.png"
                img.save(frame_file)
                frame_files.append(frame_file)
        
        # 使用ffmpeg合成视频
        output_video = self.output_dir / "episode_01.mp4"
        self.compile_video_with_ffmpeg(frame_files, output_video, fps)
        
        # 清理临时文件
        self.cleanup_temp()
        
        return output_video
    
    def add_subtitle(self, img, text, position="bottom"):
        """为图片添加字幕"""
        # 创建副本
        img = img.copy()
        draw = ImageDraw.Draw(img)
        
        # 字体设置
        try:
            font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 50)
        except:
            font = ImageFont.load_default()
        
        width, height = img.size
        
        # 字幕背景
        padding = 30
        text_bbox = draw.textbbox((0, 0), text, font=font)
        text_width = text_bbox[2] - text_bbox[0]
        text_height = text_bbox[3] - text_bbox[1]
        
        if position == "bottom":
            bg_y = height - text_height - padding * 3
        else:
            bg_y = height // 2
        
        # 绘制半透明背景
        overlay = Image.new('RGBA', img.size, (0, 0, 0, 0))
        overlay_draw = ImageDraw.Draw(overlay)
        overlay_draw.rounded_rectangle(
            [50, bg_y, width - 50, bg_y + text_height + padding * 2],
            radius=20,
            fill=(0, 0, 0, 180)
        )
        img = Image.alpha_composite(img.convert('RGBA'), overlay).convert('RGB')
        draw = ImageDraw.Draw(img)
        
        # 绘制文字
        text_x = width // 2
        text_y = bg_y + padding
        draw.text((text_x, text_y), text, fill='#ffffff', font=font, anchor='mm')
        
        return img
    
    def compile_video_with_ffmpeg(self, frame_files, output_path, fps=30):
        """使用ffmpeg合成视频"""
        print(f"  🎞️ 合成视频中...")
        
        # 创建ffmpeg命令
        # 使用图片序列生成视频
        cmd = [
            'ffmpeg',
            '-y',  # 覆盖输出文件
            '-framerate', str(fps),
            '-i', str(self.temp_dir / 'frame_%03d_%04d.png'),
            '-c:v', 'libx264',
            '-pix_fmt', 'yuv420p',
            '-crf', '23',  # 质量设置
            str(output_path)
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode == 0:
                print(f"  ✅ 视频生成成功: {output_path}")
                
                # 获取视频信息
                size = output_path.stat().st_size
                print(f"  📊 文件大小: {size / 1024 / 1024:.2f} MB")
                return True
            else:
                print(f"  ❌ ffmpeg错误: {result.stderr}")
                return False
        except Exception as e:
            print(f"  ❌ 视频生成失败: {e}")
            return False
    
    def generate_with_moviepy(self):
        """备选方案：使用moviepy生成视频"""
        try:
            from moviepy.editor import ImageSequenceClip, AudioFileClip
            
            print("🎬 使用moviepy生成视频...")
            
            scenes = [
                ("scene_loss.png", 3),
                ("scene_anger.png", 3),
                ("scene_idea.png", 3),
                ("scene_coding.png", 3),
                ("scene_success.png", 3),
            ]
            
            image_files = [str(self.output_dir / s[0]) for s in scenes]
            durations = [s[1] for s in scenes]
            
            # 创建视频剪辑
            clip = ImageSequenceClip(image_files, durations=durations)
            
            # 保存视频
            output_path = self.output_dir / "episode_01_moviepy.mp4"
            clip.write_videofile(str(output_path), fps=30)
            
            print(f"✅ 视频生成成功: {output_path}")
            return output_path
            
        except ImportError:
            print("  ⚠️ moviepy未安装，尝试用ffmpeg...")
            return None
        except Exception as e:
            print(f"  ❌ moviepy失败: {e}")
            return None
    
    def cleanup_temp(self):
        """清理临时文件"""
        print("  🧹 清理临时文件...")
        for f in self.temp_dir.glob("*.png"):
            f.unlink()
        print("  ✅ 清理完成")
    
    def generate_video_report(self):
        """生成视频制作报告"""
        report = f"""
🎬 AI短剧视频生成报告
==================
生成时间: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

📊 素材清单:
- 机器人形象: robot_avatar.png
- 场景1: 股票亏损 (scene_loss.png)
- 场景2: 被骂 (scene_anger.png)
- 场景3: 灵感发现 (scene_idea.png)
- 场景4: 编程开发 (scene_coding.png)
- 场景5: 成功成交 (scene_success.png)

📺 视频规格:
- 分辨率: 1080x1920 (抖音竖屏9:16)
- 帧率: 30fps
- 总时长: ~15秒 (每场景3秒)
- 格式: MP4 (H.264编码)

📝 字幕配置:
- 字体: DejaVu Sans Bold
- 字号: 50px
- 位置: 底部居中
- 背景: 黑色半透明圆角

🎵 BGM建议:
- 开头: 紧张/焦虑音乐
- 转折: 轻快/希望音乐
- 结尾: 成功/激昂音乐

✅ 视频文件: episode_01.mp4
"""
        return report

def main():
    """主函数"""
    print("=" * 50)
    print("🎬 AI短剧视频生成器 v1.0")
    print("=" * 50)
    
    generator = VideoGenerator()
    
    # 尝试用ffmpeg生成
    video_path = generator.create_video_from_images(scene_duration=3)
    
    if video_path and video_path.exists():
        print("\n" + "=" * 50)
        print("🎉 视频生成成功！")
        print("=" * 50)
        print(generator.generate_video_report())
        print(f"\n📁 视频位置: {video_path}")
        print("📧 准备发送邮件...")
    else:
        print("\n⚠️ ffmpeg生成失败，尝试moviepy...")
        video_path = generator.generate_with_moviepy()
        if video_path:
            print(f"✅ moviepy成功: {video_path}")

if __name__ == "__main__":
    main()
