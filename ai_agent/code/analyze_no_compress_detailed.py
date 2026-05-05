#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
分析最近 10 张图片 - 不压缩，原图直接发送，超详细分析
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
    
    # 超详细 prompt
    detailed_prompt = """请极其详细地、逐项地、完整地描述这张图片里的每一个可见元素。

要求：
1. 【整体场景】描述这是什么场景、拍摄时间（白天/夜晚/傍晚）、天气、视角（室内/室外/俯拍/平视）、拍摄环境
2. 【前景】详细描述最靠近镜头的物体：形状、颜色、大小、材质、文字、品牌、状态
3. 【中景】详细描述中间的物体和场景：布局、排列、关系
4. 【背景】描述远处的物体、建筑、天空、灯光等
5. 【文字识别】逐字逐句读取所有可见文字，不要遗漏任何招牌、标签、标语、广告、路牌上的文字
6. 【颜色与光线】描述整体色调、光源位置、光影效果
7. 【细节】描述所有容易被忽略的细节：小物件、污渍、磨损痕迹、贴纸、装饰物等
8. 【人物】如有人物，描述穿着、动作、表情、数量
9. 【车辆】如有车辆，描述品牌、颜色、型号、车牌号
10. 【建筑】描述建筑风格、楼层数、窗户、招牌、门窗、装饰

请尽可能完整、详细地输出，不要省略任何细节。如果图片中有文字，请逐字读取。"""
    
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": detailed_prompt},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]}],
        "max_tokens": 8192,
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
            'content': result  # 不截断，完整输出
        }
    else:
        return {'index': index, 'success': False, 'error': f'HTTP {r.status_code}'}

def main():
    print("=" * 80)
    print("  🔍 分析最近 10 张图片（不压缩 + 超详细）")
    print("=" * 80)
    
    images = find_images(hours=48)
    print(f"  找到 {len(images)} 张非缩略图图片 (>1KB)\n")
    
    for i, img in enumerate(images, 1):
        print(f"{i}. {img['filename']} ({img['size']//1024}KB) | {img['directory']}")
    
    print(f"\n📤 开始分析 ({len(images)} 张，不压缩，超详细描述)...\n")
    
    all_results = []
    for i, img in enumerate(images, 1):
        print(f"\n{'='*60}")
        print(f"  📷 图片 #{i}: {img['filename']}")
        print(f"  📂 {img['filepath']}")
        print(f"  📦 原图大小: {img['size']//1024}KB")
        print(f"{'='*60}")
        result = analyze_image(img['filepath'], i)
        if result['success']:
            print(f"  ✅ 耗时: {result['elapsed']:.1f}s | {result['tokens']} tokens")
            print(f"  📝 分析结果长度: {len(result['content'])} 字符")
            all_results.append(result)
        else:
            print(f"  ❌ {result['error']}")
    
    # 输出完整详细结果
    print("\n" + "=" * 80)
    print("  📋 完整详细分析结果")
    print("=" * 80)
    
    for r in all_results:
        if r['success']:
            print(f"\n{'─'*80}")
            print(f"  📷 图片 #{r['index']} - 超详细分析")
            print(f"  ⏱ {r['elapsed']:.1f}s | {r['tokens']} tokens | 原图 {r['original_kb']}KB")
            print(f"{'─'*80}")
            print(r['content'])
            print()
    
    print("=" * 80)
    print("  分析完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
