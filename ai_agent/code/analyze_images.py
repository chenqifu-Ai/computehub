#!/usr/bin/env python3
"""批量图片分析"""
import base64, requests, time

API_URL = "http://127.0.0.1:8765/v1/chat/completions"
API_KEY = "sk-78sadn09bjawde123e"
MODEL = "qwen3.6-35b"

images = [
    ("wx_camera_1777511202166.jpg", "ai_agent/results/compress_test/wx_camera_1777511202166_1536q82.jpg"),
    ("mmexport1777511387238.jpg", "ai_agent/results/compress_test/mmexport1777511387238_1536q82.jpg"),
    ("stock_check_1536q82.jpg", "ai_agent/results/compress_test/stock_check_1536q82.jpg"),
]

def analyze_image(path, prompt="请用中文简洁描述图片内容。"):
    with open(path, 'rb') as f:
        img_b64 = base64.b64encode(f.read()).decode()
    t0 = time.monotonic()
    r = requests.post(API_URL, json={
        'model': MODEL,
        'messages': [{
            'role': 'user',
            'content': [
                {'type': 'image_url', 'image_url': {'url': f'data:image/jpeg;base64,{img_b64}'}},
                {'type': 'text', 'text': prompt}
            ]
        }],
        'max_tokens': 512
    }, headers={'Authorization': f'Bearer {API_KEY}'}, timeout=30)
    elapsed = (time.monotonic() - t0) * 1000
    data = r.json()
    msg = data['choices'][0]['message']
    # content 为空时从 reasoning 取
    result = msg.get('content', '') or msg.get('reasoning', '')
    return elapsed, result

for name, path in images:
    print(f"\n{'='*60}")
    print(f"📷 {name}")
    print(f"{'='*60}")
    t, result = analyze_image(path)
    print(f"⏱️  耗时: {t:.0f}ms")
    print(f"📝 内容:\n{result}")
