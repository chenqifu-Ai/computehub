#!/usr/bin/env python3
"""
快速预览Token算力出海方案
在本地浏览器中打开HTML文件预览
"""

import os
import webbrowser
from pathlib import Path

def preview_html_files():
    """在浏览器中预览HTML文件"""
    
    html_files = [
        'token_compute_visual.html',
        'token_compute_overseas.html', 
        'token_compute_simple.html',
        'token_compute_pdf_template.html'
    ]
    
    print("🌐 Token算力出海方案预览")
    print("=" * 40)
    
    # 获取当前目录绝对路径
    current_dir = os.getcwd()
    
    for filename in html_files:
        filepath = os.path.join(current_dir, filename)
        if os.path.exists(filepath):
            # 转换为file:// URL格式
            file_url = f"file://{filepath}"
            
            print(f"📄 正在打开: {filename}")
            print(f"   📍 路径: {filepath}")
            
            # 在浏览器中打开
            webbrowser.open(file_url)
            
        else:
            print(f"❌ 文件不存在: {filename}")
    
    print("\n🎯 预览说明:")
    print("   1. 浏览器会自动打开各个HTML文件")
    print("   2. 图文并茂版 (token_compute_visual.html) 是推荐版本")
    print("   3. 图片区域显示为占位符，可按指南替换真实图片")
    print("   4. 所有文件都已发送到您的邮箱")
    
    # 显示图片指南
    guide_path = os.path.join(current_dir, 'image_guidance.md')
    if os.path.exists(guide_path):
        print(f"\n📖 图片替换指南: {guide_path}")
        print("   包含详细的图片规格和替换说明")

if __name__ == "__main__":
    preview_html_files()