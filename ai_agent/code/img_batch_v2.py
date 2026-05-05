#!/usr/bin/env python3
"""新SOP v2.0 - 批量分析最新3张图片"""
import requests, time, base64, os

IMG_DIR = "/root/.openclaw/workspace/_temp_image_recognition"
# 获取所有图片并按时间排序
files = [f for f in os.listdir(IMG_DIR) if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp'))]
files.sort(key=lambda f: os.path.getmtime(os.path.join(IMG_DIR, f)), reverse=True)
IMG_PATHS = [os.path.join(IMG_DIR, f) for f in files[:3]]  # 最新3张

URL = "http://127.0.0.1:8765/v1/chat/completions"
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer sk-78sadn09bjawde123e"}

print(f"🔧 新SOP v2.0 批量分析 | 图片数: {len(IMG_PATHS)}")
print(f"🎯 Endpoint: {URL}\n")

for i, path in enumerate(IMG_PATHS, 1):
    name = os.path.basename(path)
    size = os.path.getsize(path)
    print(f"\n{'='*60}")
    print(f"📷 第{i}张: {name} ({size/1024:.0f}KB)")
    print(f"{'='*60}")
    
    with open(path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    
    t0 = time.time()
    r = requests.post(URL, json={
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "请非常详细地描述这张图片里的所有内容。如果有文字，请完整读出所有文字内容。描述画面、颜色、布局、物体等所有细节。"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]}],
        "max_tokens": 4096,
        "temperature": 0.3
    }, headers=HEADERS, timeout=60)
    
    elapsed = time.time() - t0
    tokens = r.json().get('usage', {}).get('total_tokens', '?')
    msg = r.json()['choices'][0]['message']
    result = msg.get('content', '') or msg.get('reasoning', '')
    
    print(f"⏱️ 耗时: {elapsed:.1f}s | tokens={tokens}")
    if result:
        print(f"📝 结果:\n{result[:600]}{'...' if len(result)>600 else ''}")
    else:
        print("❌ 无输出")

print(f"\n{'='*60}")
print("✅ 批量分析完成")
print(f"{'='*60}")
