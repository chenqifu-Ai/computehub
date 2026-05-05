#!/usr/bin/env python3
"""第二阶段：并发压力测试 - 修复版"""
import requests, json, time, statistics, os, concurrent.futures, sys, traceback

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
    """单个请求，带完整错误捕获"""
    t0 = time.time()
    prompt = prompts[req_id % len(prompts)]
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": tokens_per_req,
        "temperature": 0.5
    }
    
    try:
        with requests.Session() as session:
            r = session.post(url + "/chat/completions", 
                           json=payload, 
                           headers=headers, 
                           timeout=60)
        
        elapsed = time.time() - t0
        d = r.json()
        
        if "choices" not in d:
            return {
                "req_id": req_id, "elapsed": elapsed,
                "status": "FAIL",
                "error": d.get("error", {}).get("message", "No choices")[:200]
            }
        
        msg = d["choices"][0]["message"]
        content = msg.get("content") or msg.get("reasoning", "")
        u = d.get("usage", {})
        
        return {
            "req_id": req_id, "elapsed": elapsed,
            "tokens_in": u.get("prompt_tokens", 0),
            "tokens_out": u.get("completion_tokens", 0),
            "status": "OK",
            "content_len": len(content) if content else 0
        }
    except Exception as e:
        elapsed = time.time() - t0
        return {
            "req_id": req_id, "elapsed": elapsed,
            "status": "ERROR",
            "error": str(e)[:200]
        }

def concurrent_test(url, label, concurrency, tokens_per_req, n_requests):
    """并发测试"""
    log(f"\n📊 {label}: {concurrency} 并发 × {n_requests} 请求 | max_tokens={tokens_per_req}")
    
    all_results = []
    start_all = time.time()
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        for i in range(n_requests):
            f = executor.submit(send_request, url, i, tokens_per_req)
            futures.append(f)
        
        # 收集结果
        for i, f in enumerate(concurrent.futures.as_completed(futures)):
            try:
                result = f.result(timeout=120)
                all_results.append(result)
            except Exception as e:
                all_results.append({
                    "req_id": i, "elapsed": 0,
                    "status": "TIMEOUT",
                    "error": str(e)[:200]
                })
    
    total_time = time.time() - start_all
    
    ok_results = [r for r in all_results if r["status"] == "OK"]
    error_results = [r for r in all_results if r["status"] != "OK"]
    
    if ok_results:
        times = [r["elapsed"] for r in ok_results]
        tokens_out = [r["tokens_out"] for r in ok_results]
        tokens_in = [r["tokens_in"] for r in ok_results]
        
        sorted_times = sorted(times)
        n = len(sorted_times)
        p50 = sorted_times[int(n * 0.5)]
        p90 = sorted_times[int(n * 0.9)]
        p99 = sorted_times[min(int(n * 0.99), n-1)]
        
        avg_tps_out = sum(tokens_out) / total_time if total_time > 0 else 0
        avg_tps_in = sum(tokens_in) / total_time if total_time > 0 else 0
        
        report = {
            "port": label, "concurrency": concurrency, "n_requests": n_requests,
            "tokens_per_req": tokens_per_req, "total_time": f"{total_time:.2f}s",
            "success": f"{len(ok_results)}/{len(all_results)}",
            "error_rate": f"{len(error_results)}/{len(all_results)} ({len(error_results)/len(all_results)*100:.1f}%)",
            "avg_time": f"{statistics.mean(times):.3f}s",
            "p50_time": f"{p50:.3f}s", "p90_time": f"{p90:.3f}s", "p99_time": f"{p99:.3f}s",
            "min_time": f"{min(times):.3f}s", "max_time": f"{max(times):.3f}s",
            "avg_tokens_in": f"{statistics.mean(tokens_in):.1f}",
            "avg_tokens_out": f"{statistics.mean(tokens_out):.1f}",
            "avg_tps_in": f"{avg_tps_in:.1f} t/s", "avg_tps_out": f"{avg_tps_out:.1f} t/s",
            "reqs_per_sec": f"{len(ok_results)/total_time:.1f} req/s"
        }
        
        log(f"  ✅ {report['success']} | 总耗时 {total_time:.2f}s")
        log(f"  P50={p50:.3f}s P90={p90:.3f}s P99={p99:.3f}s")
        log(f"  TPS: {avg_tps_out:.1f} out / {avg_tps_in:.1f} in | RPS: {report['reqs_per_sec']}")
        return report
    else:
        log(f"  ❌ 全部失败！错误样本:")
        if error_results:
            err = error_results[0]
            log(f"    {err['status']}: {err.get('error', 'No error detail')[:100]}")
        return {"error": "all_failed"}

log("=" * 60)
log("📊 第二阶段：并发压力测试 (修复版)")
log("=" * 60)

test_results = []

# 短请求并发
log("\n" + "=" * 50)
log("🔥 短请求 (max_tokens=32)")
log("=" * 50)

for port, url, label in [("8000", URL_8000, "8000"), ("8001", URL_8001, "8001")]:
    for n in [5, 10, 20, 30, 50]:
        r = concurrent_test(url, label, n, 32, n)
        if "error" not in r:
            test_results.append(r)
        time.sleep(1)

# 中等请求
log("\n" + "=" * 50)
log("🔥 中等请求 (max_tokens=256)")
log("=" * 50)

for port, url, label in [("8000", URL_8000, "8000"), ("8001", URL_8001, "8001")]:
    for n in [3, 5, 8, 10]:
        r = concurrent_test(url, label, n, 256, n)
        if "error" not in r:
            test_results.append(r)
        time.sleep(1)

# 长请求
log("\n" + "=" * 50)
log("🔥 长请求 (max_tokens=1024)")
log("=" * 50)

for port, url, label in [("8000", URL_8000, "8000"), ("8001", URL_8001, "8001")]:
    for n in [2, 3, 5]:
        r = concurrent_test(url, label, n, 1024, n)
        if "error" not in r:
            test_results.append(r)
        time.sleep(2)

# 保存
os.makedirs("/root/.openclaw/workspace/ai_agent/results", exist_ok=True)
with open("/root/.openclaw/workspace/ai_agent/results/test_2_concurrency.json", "w") as f:
    json.dump(test_results, f, indent=2, ensure_ascii=False)

log("\n" + "=" * 60)
log(f"✅ 第二阶段完成 | 共 {len(test_results)} 项")
log("📌 结果已保存: ai_agent/results/test_2_concurrency.json")
