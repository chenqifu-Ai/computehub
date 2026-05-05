#!/usr/bin/env python3
"""图片识别 SOP 流程 - IMG-REC-001"""
import requests, time, base64

IMG_PATHS = [
    "ai_agent/results/compress_test/wx_camera_1777511202166_1536q82.jpg",
    "ai_agent/results/compress_test/mmexport1777511387238_1536q82.jpg",
    "ai_agent/results/compress_test/stock_check_1536q82.jpg",
]

URL = "http://58.23.129.98:8001/v1/chat/completions"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer sk-78sadn09bjawde123e"
}
MODEL = "qwen3.6-35b"
MAX_TOKENS = 4096
TEMP = 0.3
TIMEOUT = 180

def analyze_with_sop(img_path):
    """按 SOP 流程分析图片"""
    print(f"\n{'='*60}")
    print(f"📷 {img_path}")
    print(f"{'='*60}")
    
    # 第 1 步：确认图片存在
    try:
        with open(img_path, 'rb') as f:
            data = f.read()
        file_size = len(data) / 1024
        print(f"✅ 图片存在，大小: {file_size:.0f} KB")
        
        if file_size > 5120:  # 5MB
            print(f"⚠️ 警告: 图片超过 5MB，base64 编码后可能超时")
            
    except FileNotFoundError:
        print(f"❌ 图片不存在: {img_path}")
        return None
    
    # 第 2 步：获取图片大小
    b64 = base64.b64encode(data).decode()
    print(f"📏 base64 编码后: {len(b64)/1024:.0f} KB")
    
    # 第 3 步：构建 API 请求
    payload = {
        "model": MODEL,
        "messages": [{"role": "user", "content": [
            {
                "type": "text", 
                "text": "请非常详细地描述这张图片里的所有内容。如果有文字，请完整读出所有文字内容。描述画面、颜色、布局、物体等所有细节。"
            },
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]}],
        "max_tokens": MAX_TOKENS,
        "temperature": TEMP
    }
    
    # 第 5 步：发送请求并获取结果
    print(f"🚀 发送请求到 {URL}...")
    start = time.time()
    try:
        r = requests.post(URL, json=payload, headers=HEADERS, timeout=TIMEOUT)
        elapsed = time.time() - start
        data = r.json()
        
        tokens = data.get('usage', {}).get('total_tokens', '?')
        print(f"⏱️ 耗时: {elapsed:.1f}s | HTTP {r.status_code} | tokens={tokens}")
        
        # 第 6 步：读取结果
        msg = data.get('choices', [{}])[0].get('message', {})
        content = msg.get('content', '')
        reasoning = msg.get('reasoning', '')
        
        if content:
            result = content
        elif reasoning:
            result = reasoning
        else:
            result = "❌ 无输出"
        
        # 第 7 步：组织回复
        print(f"📝 分析结果:\n{result}")
        return result
        
    except Exception as e:
        print(f"❌ 请求失败: {e}")
        return None

# 执行 SOP
if __name__ == "__main__":
    print("🔧 图片识别 SOP 流程启动 (IMG-REC-001)")
    print(f"🎯 标准 endpoint: {URL}")
    
    for path in IMG_PATHS:
        analyze_with_sop(path)
    
    print(f"\n{'='*60}")
    print("✅ SOP 流程完成")
    print(f"{'='*60}")
