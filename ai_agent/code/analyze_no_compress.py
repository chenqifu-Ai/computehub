#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析最近 10 张图片 - 不压缩，原图直接分析 (SOP IMG-REC-001)
"""
import os, json, time, base64, requests

API_URL = "http://127.0.0.1:8765/v1/chat/completions"
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer sk-78sadn09bjawde123e"}

def find_images(hours=48):
    search_dirs = ["/storage/emulated/0/Pictures", "/storage/emulated/0/DCIM"]
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
                if '.thumbnails' in root or '_thumbnail' in root:
                    continue
                try:
                    fp = os.path.join(root, f)
                    stat = os.stat(fp)
                    if stat.st_mtime >= cutoff and stat.st_size > 1000:
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

def analyze_image(filepath, index):
    with open(filepath, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    original_size = os.path.getsize(filepath)
    
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "请非常详细地描述这张图片的内容。包括所有文字、按钮、数字、布局、颜色等。"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]}],
        "max_tokens": 4096,
        "temperature": 0.3
    }
    
    start = time.time()
    r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=300)
    elapsed = time.time() - start
    
    if r.status_code == 200:
        data = r.json()
        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
        reasoning = data.get('choices', [{}])[0].get('message', {}).get('reasoning', '')
        result = content or reasoning
        tokens = data.get('usage', {}).get('total_tokens', '?')
        return {
            'index': index,
            'success': True,
            'elapsed': elapsed,
            'tokens': tokens,
            'original_kb': original_size // 1024,
            'content': result[:3000]
        }
    else:
        return {'index': index, 'success': False, 'error': f'HTTP {r.status_code}'}

def main():
    print("=" * 70)
    print("  🔍 分析最近 10 张图片（不压缩）")
    print("=" * 70)
    
    images = find_images(hours=48)
    print(f"  找到 {len(images)} 张非缩略图图片 (>1KB)\n")
    
    for i, img in enumerate(images, 1):
        print(f"{i}. {img['filename']} ({img['size']//1024}KB) | {img['directory']}")
    
    print(f"\n📤 开始分析 ({len(images)} 张，不压缩，原图直接发送)...\n")
    
    for i, img in enumerate(images, 1):
        print(f"\n{'─'*50}")
        print(f"  📷 #{i}: {img['filename']} ({img['size']//1024}KB)")
        print(f"  📂 {img['filepath']}")
        result = analyze_image(img['filepath'], i)
        if result['success']:
            print(f"  ✅ {result['elapsed']:.1f}s | {result['tokens']} tokens | 原图 {result['original_kb']}KB")
            print(f"  📝 {result['content'][:500]}...")
        else:
            print(f"  ❌ {result['error']}")
    
    print("\n" + "=" * 70)
    print("  分析完成")
    print("=" * 70)

if __name__ == "__main__":
    main()
