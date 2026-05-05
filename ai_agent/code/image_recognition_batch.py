#!/usr/bin/env python3
"""批量图片识别 - 使用 qwen3.6-35b 本地 API (127.0.0.1:8765)"""
import requests, json, time, base64, os, sys

API_URL = "http://127.0.0.1:8765/v1/chat/completions"
API_KEY = "sk-78sadn09bjawde123e"
HEADERS = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}

IMAGE_DIRS = [
    "/root/.openclaw/workspace/_temp_image_recognition/20260501-new",
    "/root/.openclaw/workspace/_temp_image_recognition/20260501-camera",
]

def get_images():
    imgs = []
    for d in IMAGE_DIRS:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                imgs.append({"path": os.path.join(d, f), "name": f, "dir": os.path.basename(d)})
    return imgs

def analyze_image(img_path):
    with open(img_path, "rb") as f:
        img_data = f.read()
    
    # For large images (>5MB), compress first
    if len(img_data) > 5 * 1024 * 1024:
        # Use simple quality reduction via base64 truncation is complex
        # Instead, just note it might take longer
        pass
    
    b64 = base64.b64encode(img_data).decode()
    
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [
            {"type": "text", "text": "请详细描述这张图片的所有内容：1)图片类型(截图/拍照) 2)场景描述 3)关键文字和数字 4)用途判断。用中文回答。"},
            {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}}
        ]}],
        "max_tokens": 2048,
        "temperature": 0.3
    }
    
    start = time.time()
    r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=120)
    elapsed = time.time() - start
    
    if r.status_code != 200:
        return f"HTTP {r.status_code}", elapsed, None, r.text[:200]
    
    data = r.json()
    content = data.get('choices',[{}])[0].get('message',{}).get('content','')
    reasoning = data.get('choices',[{}])[0].get('message',{}).get('reasoning','')
    result = content or reasoning or "❌ 无输出"
    usage = data.get('usage', {})
    return result, elapsed, usage, None

if __name__ == "__main__":
    images = get_images()
    sys.stdout.write(f"📷 找到 {len(images)} 张图片，开始分析...\n\n")
    sys.stdout.flush()
    
    results = []
    total_start = time.time()
    
    for i, img in enumerate(images, 1):
        fname = img["name"]
        dir_tag = img["dir"]
        size_mb = round(os.path.getsize(img["path"]) / 1024 / 1024, 2)
        
        sys.stdout.write(f"[{i}/{len(images)}] {fname} ({dir_tag}, {size_mb}MB) ... ")
        sys.stdout.flush()
        
        try:
            result, elapsed, usage, err = analyze_image(img["path"])
            first_line = result.split('\n')[0][:120] if isinstance(result, str) else str(result)[:120]
            sys.stdout.write(f"{elapsed:.1f}s\n")
            sys.stdout.write(f"  → {first_line}\n")
            sys.stdout.flush()
            
            results.append({
                "file": fname, "dir": dir_tag, "size_mb": size_mb,
                "time_s": round(elapsed, 1), "result": result, "usage": usage
            })
        except Exception as e:
            sys.stdout.write(f"ERROR: {e}\n")
            sys.stdout.flush()
            results.append({"file": fname, "dir": dir_tag, "error": str(e)})
        
        time.sleep(0.3)
    
    total_time = time.time() - total_start
    
    # Save results
    out_dir = "/root/.openclaw/workspace/ai_agent/results"
    os.makedirs(out_dir, exist_ok=True)
    out_file = f"{out_dir}/image_recognition_20260501.json"
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    # Summary
    summary_lines = [f"## 📸 图片识别报告 - 2026-05-01\n", f"共 {len(results)} 张 | 总耗时 {total_time:.0f}s | 平均 {total_time/len(results):.1f}s/张\n"]
    for r in results:
        fname = r.get("file", "?")
        dir_tag = r.get("dir", "?")
        time_s = r.get("time_s", "?")
        result = r.get("result", r.get("error", "?"))
        first_line = result.split('\n')[0] if isinstance(result, str) else str(result)
        summary_lines.append(f"\n### 📷 {fname} ({dir_tag})\n")
        summary_lines.append(f"- 耗时: {time_s}s\n")
        summary_lines.append(f"- 内容: {first_line}\n")
    
    summary_file = f"{out_dir}/image_recognition_20260501_summary.txt"
    with open(summary_file, "w", encoding="utf-8") as f:
        f.writelines(summary_lines)
    
    sys.stdout.write(f"\n✅ 完成！\n")
    sys.stdout.write(f"📋 摘要: {summary_file}\n")
    sys.stdout.write(f"⏱ 总耗时: {total_time:.0f}s\n")
    sys.stdout.flush()
