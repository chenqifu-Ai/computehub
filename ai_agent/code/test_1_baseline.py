#!/usr/bin/env python3
"""
测试计划 - 第一阶段：基线测试 (Baseline)
目标：建立性能基准，了解单请求极限
"""
import requests, json, time, statistics, os

BASE_URLS = {
    "8000": "http://58.23.129.98:8000/v1",
    "8001": "http://58.23.129.98:8001/v1",
}
API_KEY = "sk-78sadn09bjawde123e"
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

# 结果存储
results = {port: {} for port in BASE_URLS}
metrics = {"ports": list(BASE_URLS.keys()), "tests": [], "log": []}

def log(msg):
    print(msg)
    metrics["log"].append(msg)

def test_ttft(port, url, desc, stream=False):
    """测试首Token延迟"""
    key = f"ttft_{desc}"
    times = []
    n_rounds = 5
    for i in range(n_rounds):
        t0 = time.time()
        if stream:
            r = requests.post(url, json={
                "model": "qwen3.6-35b", "messages": [{"role":"user","content":"一"}],
                "max_tokens": 1, "temperature": 0.1, "stream": True
            }, headers=HEADERS, timeout=30, stream=True)
            ttft = None
            for line in r.iter_lines():
                if line:
                    line = line.decode()
                    if line.startswith("data: ") and line != "data: [DONE]":
                        try:
                            chunk = json.loads(line[6:])
                            delta = chunk["choices"][0].get("delta", {})
                            text = delta.get("content") or delta.get("reasoning") or ""
                            if text:
                                if ttft is None:
                                    ttft = time.time() - t0
                                    times.append(ttft)
                                    break
                        except:
                            pass
        else:
            r = requests.post(url, json={
                "model": "qwen3.6-35b", "messages": [{"role":"user","content":"一"}],
                "max_tokens": 1, "temperature": 0.1
            }, headers=HEADERS, timeout=30)
            elapsed = time.time() - t0
            times.append(elapsed)
        time.sleep(0.1)
    
    if times:
        p50 = statistics.median(times)
        p90 = sorted(times)[int(len(times)*0.9)]
        p99 = sorted(times)[int(len(times)*0.99)]
        avg = statistics.mean(times)
        result = {"p50": f"{p50:.3f}s", "p90": f"{p90:.3f}s", "p99": f"{p99:.3f}s", "avg": f"{avg:.3f}s"}
        results[port][key] = result
        metrics["tests"].append({"port": port, "key": key, "result": result})
        log(f"  ✅ {key}: avg={avg:.3f}s, p50={p50:.3f}s, p90={p90:.3f}s")
        return result
    log(f"  ❌ {key}: 无有效数据")

def test_latency(port, url, desc, max_tokens, temperature=0.7):
    """测试完整响应延迟"""
    key = f"latency_{desc}"
    times = []
    tokens_out = []
    for _ in range(5):
        t0 = time.time()
        r = requests.post(url, json={
            "model": "qwen3.6-35b", 
            "messages": [{"role":"user","content": f"用{max_tokens}字介绍自己"}],
            "max_tokens": max_tokens, "temperature": temperature
        }, headers=HEADERS, timeout=120)
        elapsed = time.time() - t0
        d = r.json()
        u = d.get("usage", {})
        tokens_out.append(u.get("completion_tokens", 0))
        times.append(elapsed)
        time.sleep(0.1)
    
    result = {
        "avg_time": f"{statistics.mean(times):.3f}s",
        "p50_time": f"{statistics.median(times):.3f}s",
        "avg_tokens": f"{statistics.mean(tokens_out):.1f}",
        "tps": f"{statistics.mean(tokens_out)/statistics.mean(times):.1f} t/s"
    }
    results[port][key] = result
    metrics["tests"].append({"port": port, "key": key, "result": result})
    log(f"  ✅ {key}: avg={result['avg_time']}, tokens={result['avg_tokens']}, tps={result['tps']}")
    return result

def test_streaming_tps(port, url):
    """测试流式生成速度"""
    key = "streaming_tps"
    tps_list = []
    for _ in range(3):
        r = requests.post(url, json={
            "model": "qwen3.6-35b",
            "messages": [{"role":"user","content":"写一首诗"}],
            "max_tokens": 512, "temperature": 0.7, "stream": True
        }, headers=HEADERS, timeout=120, stream=True)
        t0 = time.time()
        count = 0
        for line in r.iter_lines():
            if line:
                line = line.decode()
                if line.startswith("data: ") and line != "data: [DONE]":
                    try:
                        chunk = json.loads(line[6:])
                        delta = chunk["choices"][0].get("delta", {})
                        text = delta.get("content") or delta.get("reasoning") or ""
                        if text:
                            count += len(text)
                    except:
                        pass
        elapsed = time.time() - t0
        if elapsed > 0:
            tps_list.append(count / elapsed)
            log(f"    流式TPS: {count/elapsed:.1f} chars/s ({count} chars in {elapsed:.2f}s)")
    
    if tps_list:
        result = {"avg_tps": f"{statistics.mean(tps_list):.1f} chars/s"}
        results[port][key] = result
        metrics["tests"].append({"port": port, "key": key, "result": result})
        log(f"  ✅ {key}: avg={result['avg_tps']}")
    return result

def test_long_output(port, url):
    """长输出测试 (max_tokens=2048)"""
    key = "long_output"
    times = []
    tokens = []
    for _ in range(3):
        t0 = time.time()
        r = requests.post(url, json={
            "model": "qwen3.6-35b",
            "messages": [{"role":"user","content":"写一篇关于人工智能的短文"}],
            "max_tokens": 2048, "temperature": 0.7
        }, headers=HEADERS, timeout=300)
        elapsed = time.time() - t0
        d = r.json()
        u = d.get("usage", {})
        tokens.append(u.get("completion_tokens", 0))
        times.append(elapsed)
        log(f"    第{len(times)}次: {u.get('completion_tokens',0)} tokens, {elapsed:.2f}s, {u.get('completion_tokens',0)/max(elapsed,0.01):.1f} t/s")
    
    result = {
        "avg_tokens": f"{statistics.mean(tokens):.0f}",
        "avg_time": f"{statistics.mean(times):.2f}s",
        "avg_tps": f"{statistics.mean(tokens)/statistics.mean(times):.1f} t/s"
    }
    results[port][key] = result
    metrics["tests"].append({"port": port, "key": key, "result": result})
    log(f"  ✅ {key}: avg={result['avg_tokens']} tokens, avg={result['avg_time']}, tps={result['avg_tps']}")
    return result

# ============ 主测试流程 ============
log("=" * 60)
log("📊 第一阶段：基线测试 (Baseline)")
log("=" * 60)

for port_name, url in BASE_URLS.items():
    log(f"\n{'='*50}")
    log(f"🔧 测试端口: {port_name}")
    log(f"{'='*50}")
    
    # 1.1 连接性
    log(f"\n[1.1] 连接性测试")
    t0 = time.time()
    r = requests.get(f"{url}/models", headers=HEADERS, timeout=10)
    conn_time = time.time() - t0
    model_count = len(r.json().get("data", []))
    log(f"  HTTP {r.status_code} | {conn_time:.3f}s | {model_count} 个模型")
    metrics["tests"].append({"port": port_name, "key": "connectivity", 
                             "result": {"status": r.status_code, "time": f"{conn_time:.3f}s"}})
    
    # 1.2 TTFT 冷启动
    log(f"\n[1.2] 首Token延迟 (TTFT) - 非流式 x5")
    test_ttft(port_name, url, "nonstream")
    
    # 1.3 TTFT 流式
    log(f"\n[1.3] 首Token延迟 (TTFT) - 流式 x5")
    test_ttft(port_name, url, "stream")
    
    # 1.4 短文本
    log(f"\n[1.4] 短文本响应 (max_tokens=10) x5")
    test_latency(port_name, url, "short_10", max_tokens=10, temperature=0.1)
    
    # 1.5 中等文本
    log(f"\n[1.5] 中等文本响应 (max_tokens=256) x5")
    test_latency(port_name, url, "medium_256", max_tokens=256, temperature=0.7)
    
    # 1.6 流式TPS
    log(f"\n[1.6] 流式生成速度")
    test_streaming_tps(port_name, url)
    
    # 1.7 长文本
    log(f"\n[1.7] 长文本生成 (max_tokens=2048) x3")
    test_long_output(port_name, url)
    
    time.sleep(1)

# ============ 汇总 ============
log("\n" + "=" * 60)
log("📊 测试汇总")
log("=" * 60)

for port_name in BASE_URLS.keys():
    log(f"\n{'─'*40}")
    log(f"📋 {port_name}")
    log(f"{'─'*40}")
    for key, result in results[port_name].items():
        log(f"  {key}: {result}")

# 保存结果
os.makedirs("/root/.openclaw/workspace/ai_agent/results", exist_ok=True)
with open("/root/.openclaw/workspace/ai_agent/results/test_1_baseline.json", "w") as f:
    json.dump(metrics, f, indent=2, ensure_ascii=False)

log(f"\n✅ 结果已保存: ai_agent/results/test_1_baseline.json")
log("📌 第一阶段完成，等待执行第二阶段：并发压力测试")
