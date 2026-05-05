#!/usr/bin/env python3
"""用 Qwen-VL 视觉模型分析图片"""
import base64, json, os, sys
import subprocess

IMAGE_DIRS = [
    "/root/.openclaw/workspace/_temp_image_recognition/20260501-new",
    "/root/.openclaw/workspace/_temp_image_recognition/20260501-camera",
]

def get_all_images():
    imgs = []
    for d in IMAGE_DIRS:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                fp = os.path.join(d, f)
                sz = os.path.getsize(fp)
                # Get dimensions
                w, h = "?x?", 0
                with open(fp, 'rb') as fh:
                    all_data = fh.read()
                    pos = 2
                    while pos < len(all_data) - 8:
                        if all_data[pos:pos+2] in (b'\xff\xc0', b'\xff\xc2'):
                            h = int.from_bytes(all_data[pos+5:pos+7], 'big')
                            w = int.from_bytes(all_data[pos+7:pos+9], 'big')
                            break
                        elif all_data[pos:pos+2] == b'\xff\xd9':
                            break
                        elif all_data[pos:pos+2] == b'\xff':
                            m = all_data[pos+1]
                            if m in (0x00, 0xFF):
                                pos += 2
                            elif pos + 3 < len(all_data):
                                pos += int.from_bytes(all_data[pos+2:pos+4], 'big')
                            else:
                                break
                        else:
                            pos += 1
                img_dir = d.split('/')[-1]
                imgs.append({
                    "path": fp,
                    "name": f,
                    "dir": img_dir,
                    "size_mb": round(sz/1024/1024, 2),
                    "dims": f"{w}x{h}",
                })
    return imgs

def analyze_with_qwen_wl(img_info):
    """使用通义千问视觉模型分析图片"""
    fp = img_info["path"]
    name = img_info["name"]
    dir_tag = img_info["dir"]
    
    # Read image as base64
    with open(fp, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()
    
    prompt = f"""请详细分析这张手机截图/照片，包括：
1. 图片类型（截图/拍照/应用界面等）
2. 具体内容描述
3. 提取关键文字/数字信息
4. 判断图片的用途和场景

用简洁的中文回答。"""
    
    payload = {
        "model": "qwen-vl-plus",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"image": f"data:image/jpeg;base64,{b64}"},
                        {"text": prompt}
                    ]
                }
            ]
        },
        "parameters": {
            "max_tokens": 2048
        }
    }
    
    headers = {
        "Authorization": f"Bearer {os.environ.get('DASHSCOPE_API_KEY', '')}",
        "Content-Type": "application/json"
    }
    
    try:
        resp = subprocess.run(
            ["curl", "-s", "-X", "POST", "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions",
             "-H", f"Authorization: Bearer {os.environ.get('DASHSCOPE_API_KEY', '')}",
             "-H", "Content-Type: application/json",
             "-d", json.dumps(payload, ensure_ascii=False)],
            capture_output=True, text=True, timeout=60
        )
        result = json.loads(resp.stdout)
        if "choices" in result:
            return result["choices"][0]["message"]["content"]
        return json.dumps(result, ensure_ascii=False)[:500]
    except Exception as e:
        return f"Error: {e}"

def analyze_with_aliyun_vl(img_info):
    """使用阿里云百炼 DashScope原生 API"""
    fp = img_info["path"]
    dir_tag = img_info["dir"]
    
    with open(fp, "rb") as f:
        img_bytes = f.read()
    
    payload = {
        "model": "qwen-vl-plus",
        "input": {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {"image": img_bytes},
                        {"text": f"请详细分析这张{dir_tag}的图片，描述内容、提取文字、判断用途。简洁中文回答。"}
                    ]
                }
            ]
        },
        "parameters": {"max_tokens": 2048}
    }
    
    headers = {
        "Authorization": f"Bearer {os.environ.get('DASHSCOPE_API_KEY', '')}",
        "Content-Type": "application/json"
    }
    
    try:
        import httpx
        resp = httpx.post(
            "https://dashscope.aliyuncs.com/api/v1/services/aigc/multimodal-generation/generation",
            headers=headers,
            json=payload,
            timeout=60
        )
        return resp.text[:1000]
    except:
        return "httpx not available, trying curl"

if __name__ == "__main__":
    images = get_all_images()
    print(f"找到 {len(images)} 张图片\n")
    
    for img in images:
        print(f"\n{'='*60}")
        print(f"📷 {img['name']}")
        print(f"   目录: {img['dir']} | 大小: {img['size_mb']}MB | 尺寸: {img['dims']}")
        print(f"{'='*60}")
        
        # Try DashScope first
        result = analyze_with_qwen_wl(img)
        print(result[:800] if result else "(no result)")
        print()
