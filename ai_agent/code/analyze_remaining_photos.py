#!/usr/bin/env python3
"""分析剩余所有图片目录"""
import base64
import time
import os
import requests
from pathlib import Path

API_URL = "http://127.0.0.1:8765/v1/chat/completions"
API_KEY = "sk-78sadn09bjawde123e"
PROMPT = """请用中文简洁分析这张照片：
1. 拍的是什么场景/物体
2. 关键细节（文字、数字、日期、金额等）
3. 简要总结"""

def analyze_images(image_dir, label, max_count=10):
    """分析指定目录的图片"""
    files = sorted([f for f in Path(image_dir).glob("*") if f.suffix.lower() in ['.jpg', '.jpeg', '.png', '.bmp']], key=lambda x: x.stat().st_mtime, reverse=True)
    
    if not files:
        print(f"\n{label}: 空目录")
        return []
    
    files = files[:max_count]
    print(f"\n{'=' * 70}")
    print(f"{label} | {len(files)} 张 | {image_dir}")
    print(f"{'=' * 70}")
    
    results = []
    t0 = time.time()
    
    for i, fpath in enumerate(files, 1):
        fname = fpath.name
        fsize = fpath.stat().st_size / 1024
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
                display = content[:200].replace("\n", " ")
                print(f"    ✅ {display}")
            else:
                results.append({"name": fname, "size": f"{fsize:.0f}KB", "success": False, "error": resp.text[:200]})
                print(f"    ❌ HTTP {resp.status_code}")
        except Exception as e:
            results.append({"name": fname, "size": f"{fsize:.0f}KB", "success": False, "error": str(e)})
            print(f"    ❌ {e}")
    
    total = time.time() - t0
    print(f"\n📊 {label} 完成! 总耗时 {total:.1f}s, 成功 {sum(1 for r in results if r['success'])}/{len(results)}")
    return results

# 分析所有剩余目录
all_results = []

# 1. 相册 - 银行流水截图
results1 = analyze_images(
    "/storage/emulated/0/Pictures",
    "🏦 相册 - 银行流水截图 (ICBC)",
    max_count=5  # 先分析最近 5 张
)
all_results.extend(results1)

# 2. 微信相册
results2 = analyze_images(
    "/storage/emulated/0/Pictures/WeiXin",
    "💬 微信相册",
    max_count=5  # 先分析最近 5 张
)
all_results.extend(results2)

# 汇总
print(f"\n{'=' * 70}")
print(f"📊 总览 | 本次分析 {len(all_results)} 张")
print(f"{'=' * 70}")
print(f"✅ 成功: {sum(1 for r in all_results if r['success'])}")
print(f"❌ 失败: {sum(1 for r in all_results if not r['success'])}")
