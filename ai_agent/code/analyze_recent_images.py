#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析最近 10 张图片 - 严格按照 SOP (IMG-REC-001/002)
"""
import os, sys, json, time, base64, subprocess, requests

API_URL = "http://127.0.0.1:8765/v1/chat/completions"
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer sk-78sadn09bjawde123e"}
TEMP_DIR = "/root/.openclaw/workspace/_temp_image_recognition"
MAX_SIZE = 200 * 1024  # 200KB

def find_images(hours=48):
    search_dirs = [
        "/storage/emulated/0/Pictures",
        "/storage/emulated/0/DCIM",
    ]
    images = []
    now = time.time()
    cutoff = now - (hours * 3600)
    for d in search_dirs:
        if not os.path.exists(d):
            continue
        for root, dirs, files in os.walk(d, topdown=True, followlinks=False):
            rel = os.path.relpath(root, d)
            if rel.count(os.sep) > 3:
                dirs.clear()
                continue
            for f in files:
                if not f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                    continue
                # Skip thumbnails
                if '.thumbnails' in root or '_thumbnail' in root:
                    continue
                try:
                    fp = os.path.join(root, f)
                    stat = os.stat(fp)
                    if stat.st_mtime >= cutoff:
                        images.append({
                            'timestamp': stat.st_mtime,
                            'size': stat.st_size,
                            'filepath': fp,
                            'filename': f,
                            'directory': os.path.basename(root)
                        })
                except:
                    continue
    images.sort(key=lambda x: x['timestamp'], reverse=True)
    return images[:10]

def compress_image(filepath, max_size=MAX_SIZE):
    if not os.path.exists(filepath):
        return None
    file_size = os.path.getsize(filepath)
    if file_size <= max_size:
        return filepath
    os.makedirs(TEMP_DIR, exist_ok=True)
    output_path = f"{TEMP_DIR}/{os.path.basename(filepath)}"
    cmd = ['ffmpeg', '-y', '-i', filepath, '-q:v', '3', output_path]
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode == 0 and os.path.exists(output_path):
        new_size = os.path.getsize(output_path)
        return output_path
    return filepath

def analyze_image(filepath, index, compress=False):
    if compress:
        filepath = compress_image(filepath)
    if not filepath:
        return {'filename': os.path.basename(filepath), 'success': False, 'error': 'File not found'}
    
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": f"请非常详细地描述这张图片的内容。包括所有文字、按钮、数字、布局、颜色等。"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]}],
        "max_tokens": 4096,
        "temperature": 0.3
    }
    
    start = time.time()
    r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=180)
    elapsed = time.time() - start
    
    if r.status_code == 200:
        data = r.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        reasoning = data.get('choices', [{}])[0].get('message', {}).get('reasoning', '')
        result = content or reasoning
        tokens = data.get('usage', {}).get('total_tokens', '?')
        return {'index': index, 'success': True, 'elapsed': elapsed, 'tokens': tokens, 'content': result[:3000]}
    else:
        return {'index': index, 'success': False, 'error': f'HTTP {r.status_code}'}

def main():
    print("=" * 70)
    print("  🔍 分析最近 10 张图片")
    print("=" * 70)
    
    images = find_images(hours=48)
    print(f"  找到 {len(images)} 张非缩略图图片\n")
    
    for i, img in enumerate(images, 1):
        print(f"{i}. {img['filename']} ({img['size']//1024}KB) | {img['directory']}")
    
    print(f"\n📤 开始分析 ({len(images)} 张)...\n")
    for i, img in enumerate(images, 1):
        print(f"\n{'─'*50}")
        print(f"  📷 #{i}: {img['filename']} ({img['size']//1024}KB)")
        print(f"  📂 {img['filepath']}")
        result = analyze_image(img['filepath'], i)
        if result['success']:
            print(f"  ✅ {result['elapsed']:.1f}s | {result['tokens']} tokens")
            print(f"  📝 {result['content'][:500]}...")
        else:
            print(f"  ❌ {result['error']}")
    
    print("\n" + "=" * 70)
    print("  分析完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
