#!/usr/bin/env python3
"""SOP v2.0 新流程"""
import requests, time, base64

IMG_PATH = "/root/.openclaw/workspace/_temp_image_recognition/IMG_20260430_182515.jpg"

URL = "http://127.0.0.1:8765/v1/chat/completions"
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer sk-78sadn09bjawde123e"}

# 1. 确认存在 + 大小
import os
size = os.path.getsize(IMG_PATH)
print(f"✅ 存在: {IMG_PATH} | 大小: {size/1024:.0f} KB")

# 2. base64
with open(IMG_PATH, 'rb') as f:
    b64 = base64.b64encode(f.read()).decode()

# 3-7. 请求
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
data = r.json()
tokens = data.get('usage', {}).get('total_tokens', '?')
msg = data['choices'][0]['message']
result = msg.get('content', '') or msg.get('reasoning', '')

print(f"⏱️ 耗时: {elapsed:.1f}s | tokens={tokens}")
print(f"\n📝 结果:\n{result}")
