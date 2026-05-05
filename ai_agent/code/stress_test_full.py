#!/usr/bin/env python3
"""
暴力压力测试 — 压榨 GPU
"""
import requests, json, time, os, statistics, concurrent.futures, sys

URL_8000 = "http://58.23.129.98:8000/v1"
URL_8001 = "http://58.23.129.98:8001/v1"
API_KEY = "sk-78sadn09bjawde123e"

prompts = [
    "1+1=？直接回答数字。",
    "用一句话介绍北京。",
    "Translate to English: 深度学习。",
    "水的沸点是多少？",
    "Python 列表推导式示例。",
    "写一句关于春天的诗。",
    "量子计算是什么？",
    "杜甫最著名的诗。",
    "TCP/IP 简述。",
    "关于月亮的短诗。",
]

def log(msg):
    print(msg, flush=True)

def send_request(url, req_id, tokens_per_req=32):
    t0 = time.time()
    prompt = prompts[req_id % len(prompts)]
    try:
        with requests.Session() as session:
            r = session.post(url + "/chat/completions", 
                           json={"model":"qwen3.6-35b",
                                 "messages":[{"role":"user","content":prompt}],
                                 "max_tokens": tokens_per_req,
                                 "temperature": 0.5}, 
                           headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
                           timeout=120)
        elapsed = time.time() - t0
        d = r.json()
        if "choices" not in d:
            return {"req_id": req_id, "elapsed": elapsed, "status": "FAIL",
                    "error": d.get("error", {}).get("message", "No choices")[:200]}
        msg = d["choices"][0]["message"]
        content = msg.get("content") or msg.get("reasoning", "")
        u = d.get("usage", {})
        return {"req_id": req_id, "elapsed": elapsed, "tokens_in": u.get("prompt_tokens", 0),
                "tokens_out": u.get("completion_tokens", 0), "status": "OK"}
    except Exception as e:
        return {"req_id": req_id, "elapsed": time.time()-t0, "status": "ERROR", "error": str(e)[:200]}

def stress_test(url, label, concurrency, n_requests, tokens_per_req, label_extra=""):
    log(f"\n🔥 {label} × {concurrency} | {n_requests} 请求 | max_tokens={tokens_per_req} {label_extra}")
    t0_all = time.time()
    all_results = []
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(send_request, url, i, tokens_per_req) for i in range(n_requests)]
        for i, f in enumerate(concurrent.futures.as_completed(futures)):
            try:
                all_results.append(f.result(timeout=300))
            except:
                all_results.append({"req_id": i, "elapsed": 0, "status": "TIMEOUT", "error": "timeout"})
    
    total_time = time.time() - t0_all
    ok = [r for r in all_results if r["status"] == "OK"]
    fail = [r for r in all_results if r["status"] != "OK"]
    times = [r["elapsed"] for r in ok]
    t_out = [r["tokens_out"] for r in ok]
    
    if not times:
        log(f"  ❌ 全部失败")
        return None
    
    st = sorted(times)
    n = len(st)
    p50 = st[int(n*0.5)]
    p90 = st[int(n*0.9)]
    p99 = st[min(int(n*0.99), n-1)]
    
    tps_out = sum(t_out) / total_time
    tps_in = sum(r["tokens_in"] for r in ok) / total_time
    
    log(f"  ✅ {len(ok)}/{len(all_results)} | 总耗时 {total_time:.2f}s")
    log(f"     P50={p50:.3f}s P90={p90:.3f}s P99={p99:.3f}s")
    log(f"     TPS: {tps_out:.0f} out / {tps_in:.0f} in | RPS: {len(ok)/total_time:.1f}")
    
    return {"port": label, "concurrency": concurrency, "n_requests": n_requests,
            "tokens_per_req": tokens_per_req, "total_time": f"{total_time:.2f}s",
            "success": f"{len(ok)}/{len(all_results)}", "p50": f"{p50:.3f}s",
            "p90": f"{p90:.3f}s", "p99": f"{p99:.3f}s",
            "tps_out": f"{tps_out:.0f}", "tps_in": f"{tps_in:.0f}",
            "rps": f"{len(ok)/total_time:.1f}"}

log("=" * 60)
log("💥 暴力压力测试")
log("=" * 60)

all_results = []

# === 第一阶段: 阶梯并发找极限 ===
log("\n" + "=" * 50)
log("📈 短请求阶梯并发 (max_tokens=32)")
log("=" * 50)

for port, url, label in [("8000", URL_8000, "8000"), ("8001", URL_8001, "8001")]:
    for n in [50, 100, 200, 500, 1000]:
        r = stress_test(url, label, n, n, 32)
        if r: all_results.append(r)
        if n >= 1000: break  # 1000已经是极限了

# === 第二阶段: 混合并发 ===
log("\n" + "=" * 50)
log("📈 中等请求 (max_tokens=256)")
log("=" * 50)

for port, url, label in [("8000", URL_8000, "8000"), ("8001", URL_8001, "8001")]:
    for n in [20, 50, 80, 100]:
        r = stress_test(url, label, n, n, 256)
        if r: all_results.append(r)

# === 第三阶段: 长输出 ===
log("\n" + "=" * 50)
log("📈 长请求 (max_tokens=1024)")
log("=" * 50)

for port, url, label in [("8000", URL_8000, "8000"), ("8001", URL_8001, "8001")]:
    for n in [10, 20, 30]:
        r = stress_test(url, label, n, n, 1024)
        if r: all_results.append(r)

# === 第四阶段: 极端混合 ===
log("\n" + "=" * 50)
log("📈 超长请求 (max_tokens=2048)")
log("=" * 50)

for port, url, label in [("8000", URL_8000, "8000"), ("8001", URL_8001, "8001")]:
    for n in [5, 10, 15]:
        r = stress_test(url, label, n, n, 2048)
        if r: all_results.append(r)

# 保存
os.makedirs("/root/.openclaw/workspace/ai_agent/results", exist_ok=True)
with open("/root/.openclaw/workspace/ai_agent/results/stress_test_full.json", "w") as f:
    json.dump(all_results, f, indent=2, ensure_ascii=False)

log("\n" + "=" * 60)
log(f"✅ 暴力测试完成 | {len(all_results)} 项")
log("📌 结果已保存: ai_agent/results/stress_test_full.json")
