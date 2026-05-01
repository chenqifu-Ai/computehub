#!/usr/bin/env python3
"""分析 Camera 目录的新照片"""
import base64
import time
import os
import requests

API_URL = "http://127.0.0.1:8765/v1/chat/completions"
API_KEY = "sk-78sadn09bjawde123e"
IMAGES_DIR = "/root/.openclaw/workspace/_temp_image_recognition/20260501-camera"

PROMPT = """请用中文简洁分析这张照片：
1. 拍的是什么场景/物体
2. 关键细节（文字、数字、人物、物品等）
3. 简要总结"""

files = sorted([f for f in os.listdir(IMAGES_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png'))])

print("=" * 70)
print(f"📸 Camera 照片分析 | {len(files)} 张")
print("=" * 70)

results = []
t0 = time.time()

for i, fname in enumerate(files, 1):
    fpath = os.path.join(IMAGES_DIR, fname)
    fsize = os.path.getsize(fpath) / 1024
    print(f"\n[{i}/{len(files)}] {fname} ({fsize:.0f}KB)")
    
    with open(fpath, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode()
    
    payload = {
        "model": "qwen3.6-35b",
        "max_tokens": 1024,
        "temperature": 0.3,
        "messages": [{
            "role": "user",
            "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"}},
                {"type": "text", "text": PROMPT}
            ]
        }]
    }
    
    t_start = time.time()
    try:
        resp = requests.post(API_URL, json=payload, headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }, timeout=120)
        elapsed = time.time() - t_start
        
        if resp.status_code == 200:
            data = resp.json()
            content = ""
            if data.get("choices"):
                msg = data["choices"][0].get("message", {})
                content = msg.get("content", "") or msg.get("reasoning", "")
            if not content:
                content = "(无法提取内容)"
            
            results.append({"name": fname, "size": f"{fsize:.0f}KB", "success": True, "content": content, "time": f"{elapsed:.1f}s"})
            display = content[:300].replace("\n", "\n    ")
            print(f"    ✅ {display}")
        else:
            results.append({"name": fname, "size": f"{fsize:.0f}KB", "success": False, "error": resp.text[:200]})
            print(f"    ❌ HTTP {resp.status_code}")
    except Exception as e:
        results.append({"name": fname, "size": f"{fsize:.0f}KB", "success": False, "error": str(e)})
        print(f"    ❌ {e}")

total = time.time() - t0
print(f"\n{'=' * 70}")
print(f"📊 完成! 总耗时 {total:.1f}s, 成功 {sum(1 for r in results if r['success'])}/{len(results)}")
