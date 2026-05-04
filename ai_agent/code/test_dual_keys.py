#!/usr/bin/env python3
"""双 Key 全面测试"""

import requests
import time
from datetime import datetime

BASE = "https://ai.zhangtuokeji.top:9090/v1"

KEYS = [
    {"id": "Key1", "key": "sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl"},
    {"id": "Key2", "key": "sk-1G7ntp2mow9OTyn1guonubuTRDbebaYqk7YdplCdHfk3ZFZe"},
]

MODELS = ["qwen3.6-35b", "qwen3.6-35b-common"]
PROMPT = "用一句话回答：1+1等于几？"

print(f"\n{'='*100}")
print(f"  🔥 双 Key × 双模型 全面测试")
print(f"  时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"  已删除: sk-08XEev... (401 过期)")
print(f"{'='*100}\n")

all_results = []

for k in KEYS:
    print(f"  📌 {k['id']}: {k['key'][:15]}...")
    print(f"  {'─'*100}")
    
    for model in MODELS:
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {k['key']}"
        }
        body = {
            "model": model,
            "messages": [{"role": "user", "content": PROMPT}],
            "max_tokens": 2048,
            "temperature": 0.7
        }
        
        start = time.perf_counter()
        try:
            r = requests.post(f"{BASE}/chat/completions", headers=headers, json=body, timeout=30)
            lat = (time.perf_counter() - start) * 1000
            
            if r.status_code == 200:
                data = r.json()
                msg = data["choices"][0]["message"]
                content = msg.get("content") or ""
                reasoning = msg.get("reasoning") or ""
                finish = data["choices"][0].get("finish_reason", "?")
                
                all_results.append({
                    "key": k["id"],
                    "model": model,
                    "status": "OK",
                    "lat": lat,
                    "actual_model": data["model"],
                    "content_len": len(content),
                    "reasoning_len": len(reasoning),
                    "finish": finish,
                })
                
                icon = "⚡" if lat < 10000 else ("🔵" if lat < 20000 else "🐌")
                print(f"    {icon} {model:22s} → 实际:{data['model']:22s} ⏱{lat:.0f}ms 📏{len(content)}字 🧠{len(reasoning)}字 finish={finish}")
            else:
                err = r.text[:100]
                all_results.append({
                    "key": k["id"], "model": model,
                    "status": f"HTTP {r.status_code}", "lat": lat,
                    "actual_model": "-", "content_len": 0, "reasoning_len": 0,
                    "finish": "-", "error": err,
                })
                print(f"    ❌ {model:22s} → HTTP {r.status_code} {err}")
                
        except Exception as e:
            lat = (time.perf_counter() - start) * 1000
            all_results.append({
                "key": k["id"], "model": model,
                "status": f"ERROR: {str(e)[:40]}", "lat": lat,
                "actual_model": "-", "content_len": 0, "reasoning_len": 0, "finish": "-",
            })
            print(f"    ❌ {model:22s} → {e}")
    
    print()

# 总结
print(f"{'='*100}")
print(f"  📊 汇总")
print(f"{'='*100}")
print(f"{'Key':>5s} | {'请求模型':>22s} | {'实际模型':>22s} | {'状态':>12s} | {'延迟':>8s} | {'content':>8s} | {'reasoning':>10s}")
print(f"{'─'*100}")

for r in all_results:
    status_icon = "✅" if r["status"] == "OK" else "❌"
    print(f"{r['key']:>5s} | {r['model']:>22s} | {r['actual_model']:>22s} | {status_icon} {r['status']:>12s} | {r['lat']:>7.0f}ms | {r['content_len']:>7d}字 | {r['reasoning_len']:>9d}字")

# 结论
print(f"\n{'='*100}")
print(f"  📝 结论:")
for r in all_results:
    ok = r["status"] == "OK"
    c_ok = "✅正常" if ok and r["content_len"] > 0 else ("❌null" if ok else "N/A")
    print(f"    {r['key']} → {r['model']}: {c_ok}")

print(f"{'='*100}\n")
