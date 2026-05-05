#!/usr/bin/env python3
"""图片识别 SOP v2.0 - 串行优化版：压缩 + 串行"""
import requests, time, base64, os, subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# ============================================================
# 配置
# ============================================================
IMG_DIR = "/storage/emulated/0/DCIM/Camera"
NUM_IMAGES = 10  # 识别最新 N 张
MAX_COMPRESS_SIZE = 200 * 1024  # 200KB
MAX_COMPRESS_SIZE_MB = 0.5  # 不超过 500KB（质量保障）

API_URL = "http://127.0.0.1:8765/v1/chat/completions"
HEADERS = {
    "Content-Type": "application/json",
    "Authorization": "Bearer sk-78sadn09bjawde123e"
}

PROMPT = (
    "请极度详细地描述这张图片。要求：\n"
    "1. 从上到下、从左到右全面扫描画面每个区域\n"
    "2. 读出所有可见文字（招牌、车牌、标识、标语、广告等），一个字不要漏\n"
    "3. 描述所有物体的位置、颜色、形状、数量\n"
    "4. 描述人物（衣着、动作、方向、表情等）\n"
    "5. 描述光线、天气、时间推断\n"
    "6. 识别可能的地点线索（建筑风格、植被、路标、商铺类型等）\n"
    "7. 不要遗漏任何角落的细节，包括边缘部分"
)


# ============================================================
# 1. 快速发现图片
# ============================================================
def find_images():
    """直接读取相机目录，按修改时间排序"""
    files = []
    for f in sorted(os.listdir(IMG_DIR)):
        if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
            filepath = os.path.join(IMG_DIR, f)
            files.append({
                'path': filepath,
                'name': f,
                'mtime': os.path.getmtime(filepath),
                'size': os.path.getsize(filepath)
            })
    # 按时间倒序，取最新 N 张
    files.sort(key=lambda x: x['mtime'], reverse=True)
    return files[:NUM_IMAGES]


# ============================================================
# 2. 图片压缩
# ============================================================
def compress_image(filepath, max_size=MAX_COMPRESS_SIZE):
    """
    压缩图片到指定大小
    使用 ffmpeg（Termux 可用）
    """
    if not os.path.exists(filepath):
        return None

    file_size = os.path.getsize(filepath)
    if file_size <= max_size:
        return filepath  # 不需要压缩

    # 使用 ffmpeg 压缩
    temp_file = filepath.replace('.jpg', '_comp.jpg').replace('.jpeg', '_comp.jpg').replace('.png', '_comp.jpg')
    
    # 先尝试缩小尺寸
    cmd = [
        'ffmpeg', '-y', '-i', filepath,
        '-vf', 'scale=\'if(gt(iw,1920),1920,-2)\':\'if(gt(ih,1440),1440,-2)\'',  # 限制 1920x1440
        '-q:v', '2',  # JPEG 质量（更高清晰度，适合文字识别）
        temp_file
    ]
    
    result = subprocess.run(cmd, capture_output=True, timeout=30)
    if result.returncode == 0 and os.path.exists(temp_file):
        new_size = os.path.getsize(temp_file)
        # 如果还是太大，进一步降低质量
        if new_size > MAX_COMPRESS_SIZE_MB:
            cmd2 = [
                'ffmpeg', '-y', '-i', temp_file,
                '-q:v', '5',  # 更低质量
                temp_file
            ]
            subprocess.run(cmd2, capture_output=True, timeout=30)
        
        new_size = os.path.getsize(temp_file)
        return temp_file
    
    # 失败返回原图
    return filepath


# ============================================================
# 3. 图片编码
# ============================================================
def encode_image(filepath):
    """将图片编码为 base64"""
    with open(filepath, 'rb') as f:
        return base64.b64encode(f.read()).decode()


# ============================================================
# 4. API 调用（串行模式）
# ============================================================
def analyze_image(path, b64):
    """调用 qwen3.6-35b API 分析图片"""
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": PROMPT},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]}],
        "max_tokens": 8192,
        "temperature": 0.3
    }
    
    try:
        start = time.time()
        r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=180)
        elapsed = time.time() - start
        
        if r.status_code == 200:
            data = r.json()
            msg = data.get('choices', [{}])[0].get('message', {})
            result = msg.get('content', '') or msg.get('reasoning', '')
            tokens = data.get('usage', {}).get('total_tokens', '?')
            
            return {
                'success': True,
                'path': path,
                'name': os.path.basename(path),
                'elapsed': elapsed,
                'tokens': tokens,
                'result': result
            }
        else:
            return {'success': False, 'path': path, 'error': f'HTTP {r.status_code}'}
    except Exception as e:
        return {'success': False, 'path': path, 'error': str(e)}


# ============================================================
# 5. 主流程
# ============================================================
def main():
    print("=" * 60)
    print("🔧 图片识别 SOP v2.0（串行优化版：压缩 + 串行）")
    print("=" * 60)
    print(f"📁 目录: {IMG_DIR}")
    print(f"🎯 图片数: {NUM_IMAGES}")
    print(f"📐 压缩上限: {MAX_COMPRESS_SIZE//1024}KB")
    print(f"🎯 Endpoint: {API_URL}\n")
    
    # Step 1: 发现图片
    print("📷 步骤 1: 发现图片...")
    images = find_images()
    print(f"✅ 找到 {len(images)} 张\n")
    
    total_start = time.time()
    
    # Step 2-4: 串行：压缩 + 编码 + 分析
    print(f"🔄 步骤 2-4: 串行处理 {len(images)} 张图片（压缩→编码→API）\n")
    
    results = []
    for img in images:
        path = img['path']
        name = img['name']
        orig_size = img['size']
        
        print(f"📷 {name} ({orig_size//1024}KB)")
        
        start = time.time()
        
        # 压缩
        comp_path = compress_image(path)
        comp_size = os.path.getsize(comp_path) if comp_path else orig_size
        if comp_path != path:
            ratio = (1 - comp_size / orig_size) * 100
            print(f"   📦 压缩: {orig_size//1024}KB → {comp_size//1024}KB ({ratio:.0f}%)")
        else:
            print(f"   ✅ 无需压缩")
        
        # 编码
        b64 = encode_image(comp_path)
        
        # API 调用
        result = analyze_image(path, b64)
        elapsed = time.time() - start
        result['elapsed'] = elapsed
        
        status = "✅" if result.get('success') else "❌"
        if result.get('success'):
            print(f"   {status} 总耗时: {elapsed:.1f}s | {result['elapsed']:.1f}s(API) | {result['tokens']} tokens")
        else:
            print(f"   {status} {result.get('error', '未知')}")
        
        results.append(result)
    
    # 汇总
    total_time = time.time() - total_start
    success = sum(1 for r in results if r.get('success'))
    
    print(f"\n{'=' * 60}")
    print(f"📊 汇总")
    print(f"{'=' * 60}")
    print(f"总耗时: {total_time:.1f}s")
    print(f"成功: {success}/{len(results)}")
    if success > 0:
        avg_time = sum(r['elapsed'] for r in results if r['success']) / success
        api_time = sum(r['elapsed'] for r in results if r['success']) / success
        print(f"平均每张总耗时: {avg_time:.1f}s")
        print(f"平均每张 API 耗时: {api_time:.1f}s")
    print(f"{'=' * 60}")
    
    # 输出结构化结果
    print(f"\n📝 详细结果:\n")
    for r in results:
        if r.get('success'):
            print(f"--- {r['name']} ---")
            print(f"耗时: {r['elapsed']:.1f}s | API: {r['elapsed']:.1f}s | tokens: {r['tokens']}")
            print(f"内容: {r['result'][:500]}...")  # 截断
            print()


if __name__ == '__main__':
    main()
