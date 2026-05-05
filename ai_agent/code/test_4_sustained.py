#!/usr/bin/env python3
"""
第四阶段：持续压力测试
目标：长时间运行，观察稳定性和内存泄漏
"""
import requests, json, time, os, statistics, sys

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

def run_sustained_test(url, label, port, concurrency, max_tokens, duration_sec, step_sec=60):
    """持续压力测试"""
    import concurrent.futures
    
    log(f"\n{'='*60}")
    log(f"🔥 持续测试: {label} ({port})")
    log(f"   并发={concurrency}, max_tokens={max_tokens}, 持续时间={duration_sec//60}分钟")
    log(f"{'='*60}")
    
    all_times = []
    all_tokens = []
    errors = 0
    total_reqs = 0
    checkpoints = []
    start_all = time.time()
    
    # 分批次持续发送
    batch_size = concurrency
    req_counter = [0]  # mutable counter
    
    while time.time() - start_all < duration_sec:
        batch_start = time.time()
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=batch_size) as executor:
            futures = []
            for i in range(batch_size):
                prompt = prompts[req_counter[0] % len(prompts)]
                req_counter[0] += 1
                total_reqs += 1
                
                def send_req(req_id, p=prompt, m=max_tokens):
                    t0 = time.time()
                    try:
                        r = requests.post(url + "/chat/completions", json={
                            "model": "qwen3.6-35b",
                            "messages": [{"role": "user", "content": p}],
                            "max_tokens": m, "temperature": 0.5
                        }, headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}, timeout=120)
                        d = r.json()
                        elapsed = time.time() - t0
                        if "choices" in d:
                            u = d.get("usage", {})
                            tokens_out = u.get("completion_tokens", 0)
                            all_times.append(elapsed)
                            all_tokens.append(tokens_out)
                            return elapsed, tokens_out, "OK"
                        return elapsed, 0, "FAIL"
                    except Exception as e:
                        elapsed = time.time() - t0
                        return elapsed, 0, f"ERROR: {str(e)[:50]}"
                
                futures.append(executor.submit(send_req, i))
            
            # 收集结果
            for f in concurrent.futures.as_completed(futures):
                t, tok, status = f.result()
                if status != "OK":
                    errors += 1
        
        batch_elapsed = time.time() - batch_start
        checkpoint_time = time.time() - start_all
        
        # 每 step_sec 秒记录一次
        if checkpoint_time % step_sec < batch_elapsed + 1 or checkpoint_time < 10:
            if all_times:
                avg_time = statistics.mean(all_times)
                avg_tokens = statistics.mean(all_tokens)
                tps = statistics.mean(all_tokens) / statistics.mean(all_times) if all_times else 0
                checkpoint = {
                    "time_sec": f"{checkpoint_time:.0f}s",
                    "total_reqs": total_reqs,
                    "errors": errors,
                    "avg_time": f"{avg_time:.2f}s",
                    "avg_tokens": f"{avg_tokens:.0f}",
                    "tps": f"{tps:.1f}"
                }
                checkpoints.append(checkpoint)
                log(f"  ⏱  {checkpoint['time_sec']} | 请求:{total_reqs} 错误:{errors} | "
                    f"平均延迟:{checkpoint['avg_time']} | 平均tokens:{checkpoint['avg_tokens']} | TPS:{checkpoint['tps']}")
            else:
                log(f"  ⏱  {checkpoint_time:.0f}s | 请求:{total_reqs} 错误:{errors} | 无成功响应")
    
    total_time = time.time() - start_all
    
    # 最终统计
    if all_times:
        sorted_t = sorted(all_times)
        p50 = sorted_t[int(len(sorted_t)*0.5)]
        p90 = sorted_t[int(len(sorted_t)*0.9)]
        p99 = sorted_t[min(int(len(sorted_t)*0.99), len(sorted_t)-1)]
        
        final_report = {
            "port": port,
            "concurrency": concurrency,
            "max_tokens": max_tokens,
            "duration_sec": duration_sec,
            "total_time": f"{total_time:.0f}s",
            "total_reqs": total_reqs,
            "success": f"{total_reqs-errors}/{total_reqs}",
            "error_rate": f"{errors}/{total_reqs} ({errors/total_reqs*100:.1f}%)",
            "p50": f"{p50:.3f}s", "p90": f"{p90:.3f}s", "p99": f"{p99:.3f}s",
            "avg_tps": f"{statistics.mean(all_tokens)/statistics.mean(all_times):.1f} t/s",
            "checkpoints": checkpoints
        }
        
        log(f"\n{'='*50}")
        log(f"✅ 测试完成 | 总请求:{total_reqs} | 错误:{errors}")
        log(f"   P50={p50:.3f}s P90={p90:.3f}s P99={p99:.3f}s")
        log(f"   错误率: {final_report['error_rate']}")
        log(f"   稳定TPS: {final_report['avg_tps']}")
        log(f"   记录点: {len(checkpoints)} 个")
        return final_report
    else:
        log(f"❌ 全部失败！")
        return {"error": "all_failed", "port": port}

log("=" * 60)
log("📊 第四阶段：持续压力测试")
log("=" * 60)

test_results = []

# 短跑: 5分钟, 100并发
log("\n" + "=" * 50)
log("🔥 短跑压测: 5分钟, 100并发, max_tokens=64")
log("=" * 50)
for port, url, label in [("8000", URL_8000, "8000"), ("8001", URL_8001, "8001")]:
    r = run_sustained_test(url, label, port, 100, 64, 300, step_sec=60)
    if "error" not in r:
        test_results.append(r)

# 中跑: 10分钟, 50并发
log("\n" + "=" * 50)
log("🔥 中跑压测: 10分钟, 50并发, max_tokens=256")
log("=" * 50)
for port, url, label in [("8000", URL_8000, "8000"), ("8001", URL_8001, "8001")]:
    r = run_sustained_test(url, label, port, 50, 256, 600, step_sec=120)
    if "error" not in r:
        test_results.append(r)

# 保存
os.makedirs("/root/.openclaw/workspace/ai_agent/results", exist_ok=True)
with open("/root/.openclaw/workspace/ai_agent/results/test_4_sustained.json", "w") as f:
    json.dump(test_results, f, indent=2, ensure_ascii=False)

log("\n" + "=" * 60)
log(f"✅ 第四阶段完成 | 共 {len(test_results)} 项")
log("📌 结果已保存: ai_agent/results/test_4_sustained.json")
log("📌 等待第五阶段：极端参数测试")
