#!/usr/bin/env python3
"""批量图片识别分析 - 使用阿里云 DashScope Qwen-VL"""
import os
import json
import base64
import time
from pathlib import Path

IMAGE_DIR = "/root/.openclaw/workspace/_temp_image_recognition/20260501-new"
OUTPUT_DIR = "/root/.openclaw/workspace/ai_agent/results"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Try multiple API providers
API_KEYS = [
    ("https://dashscope.aliyuncs.com/compatible-mode/v1", os.environ.get("DASHSCOPE_API_KEY", "")),
    ("https://ai.zhangtuokeji.top:9090/v1", "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl"),
]

def encode_image(image_path):
    """Read image and encode to base64 for vision API"""
    with open(image_path, "rb") as f:
        return base64.b64encode(f.read()).decode()

def analyze_image_vl(image_path, image_name):
    """Use DashScope qwen-vl-plus for image analysis"""
    import subprocess
    import sys
    
    b64 = encode_image(image_path)
    
    prompt = f"""请详细分析这张图片，包括：
1. 图片内容描述（场景、物体、人物、文字等）
2. 关键文字信息提取
3. 图片用途/场景判断
4. 任何需要注意的信息

只返回分析结果，不要输出其他内容。"""
    
    payload = {
        "model": "qwen-vl-plus",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"image": f"data:image/jpeg;base64,{b64}"},
                        {"text": prompt}
                    ]
                }
            ]
        }
    }
    
    headers = {
        "Authorization": f"Bearer {API_KEYS[0][1]}",
        "Content-Type": "application/json"
    }
    
    try:
        import requests
        resp = requests.post(API_KEYS[0][0] + "/chat/completions", 
                           headers=headers, json=payload, timeout=60)
        data = resp.json()
        if "choices" in data:
            return data["choices"][0]["message"]["content"]
        return json.dumps(data, ensure_ascii=False)
    except Exception as e:
        return f"API error: {e}"

def analyze_image_simple(image_path, image_name):
    """Simple local analysis - extract EXIF and metadata"""
    try:
        import struct
        
        # Get basic file info
        file_size = os.path.getsize(image_path)
        stat = os.stat(image_path)
        
        info = {
            "name": image_name,
            "size_bytes": file_size,
            "size_mb": round(file_size / 1024 / 1024, 2),
            "modified": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_mtime)),
            "created": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(stat.st_ctime)),
        }
        
        # Try to get image dimensions
        with open(image_path, "rb") as f:
            header = f.read(24)
            if header[:2] == b'\xff\xd8':  # JPEG
                # Find SOF marker
                idx = 2
                while idx < len(header) + 1000:
                    if header[idx:idx+2] == b'\xff\xc0' or header[idx:idx+2] == b'\xff\xc2':
                        if idx + 7 < len(image_path) or True:  # might need to read more
                            f2 = open(image_path, "rb")
                            f2.seek(idx)
                            sof = f2.read(7)
                            height = struct.unpack(">H", sof[5:7])[0]
                            width = struct.unpack(">H", sof[7:9])[0] if sof[7:9] else "?"
                            # Actually let me fix this
                            pass
                        break
                    elif header[idx:idx+2] == b'\xff\xd9':  # EOI
                        break
                    idx += 1
        
    except Exception as e:
        info = {"name": image_name, "error": str(e)}
    
    return info

# List all images
image_files = sorted([
    os.path.join(IMAGE_DIR, f) 
    for f in os.listdir(IMAGE_DIR) 
    if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))
])

print(f"找到 {len(image_files)} 张图片\n")
for img in image_files:
    name = os.path.basename(img)
    size = os.path.getsize(img)
    print(f"  {name}: {size/1024/1024:.1f}MB")

print("\n开始分析...")

# Save metadata first
metadata = []
for img_path in image_files:
    name = os.path.basename(img_path)
    stat = os.stat(img_path)
    metadata.append({
        "file": name,
        "size_bytes": os.path.getsize(img_path),
        "modified": time.ctime(stat.st_mtime),
    })

meta_path = os.path.join(OUTPUT_DIR, "image_batch_meta.json")
with open(meta_path, "w", encoding="utf-8") as f:
    json.dump(metadata, f, ensure_ascii=False, indent=2)
print(f"元数据已保存: {meta_path}")

print("\n分析完成（本地元数据）")
