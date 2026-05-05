#!/usr/bin/env python3
"""批量图片分析 - 使用 Ollama 云端 qwen3-vl:235b"""
import base64, json, os, time, sys

IMAGE_DIRS = [
    "/root/.openclaw/workspace/_temp_image_recognition/20260501-new",
    "/root/.openclaw/workspace/_temp_image_recognition/20260501-camera",
]

OLLAMA_API = "https://ollama.com/api/chat"
API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"

def get_images():
    imgs = []
    for d in IMAGE_DIRS:
        if not os.path.isdir(d):
            continue
        for f in sorted(os.listdir(d)):
            if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')):
                fp = os.path.join(d, f)
                imgs.append({"path": fp, "name": f, "dir": os.path.basename(d)})
    return imgs

def analyze(img_path):
    with open(img_path, 'rb') as f:
        b64 = base64.b64encode(f.read()).decode()
    
    data = {
        "model": "qwen3-vl:235b",
        "messages": [{
            "role": "user",
            "content": "请详细分析这张图片：1)图片类型 2)具体内容描述 3)关键文字/数字 4)用途判断。用中文简洁回答。",
            "images": [b64]
        }],
        "stream": False,
        "options": {"temperature": 0.3, "num_predict": 1000}
    }
    
    import urllib.request
    req = urllib.request.Request(
        OLLAMA_API,
        data=json.dumps(data).encode(),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        },
        method="POST"
    )
    
    resp = urllib.request.urlopen(req, timeout=120, context=urllib.request.ssl._create_unverified_context())
    result = json.loads(resp.read())
    return result.get("message", {}).get("content", "(no content)")

if __name__ == "__main__":
    images = get_images()
    print(f"找到 {len(images)} 张图片，开始分析...\n")
    
    results = []
    for i, img in enumerate(images, 1):
        print(f"[{i}/{len(images)}] {img['name']} ({img['dir']})")
        t0 = time.time()
        try:
            result = analyze(img["path"])
            elapsed = time.time() - t0
            results.append({
                "file": img["name"],
                "dir": img["dir"],
                "size_mb": round(os.path.getsize(img["path"])/1024/1024, 2),
                "analysis": result,
                "time_s": round(elapsed, 1)
            })
            print(f"  ⏱ {elapsed:.1f}s → {result[:150]}")
        except Exception as e:
            elapsed = time.time() - t0
            results.append({
                "file": img["name"],
                "dir": img["dir"],
                "size_mb": round(os.path.getsize(img["path"])/1024/1024, 2),
                "analysis": f"Error: {e}",
                "time_s": round(elapsed, 1)
            })
            print(f"  ⏱ {elapsed:.1f}s → ❌ {e}")
    
    # Save results
    out_dir = "/root/.openclaw/workspace/ai_agent/results"
    os.makedirs(out_dir, exist_ok=True)
    with open(f"{out_dir}/image_analysis_20260501.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 完成！结果已保存: {out_dir}/image_analysis_20260501.json")
    print(f"📊 总耗时: {sum(r['time_s'] for r in results):.0f}s, 平均: {sum(r['time_s'] for r in results)/len(results):.1f}s/张")
