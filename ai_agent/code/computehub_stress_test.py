#!/usr/bin/env python3
"""
ComputeHub Worker 压力测试脚本 v2
- 修复API格式: command 为顶层字段
- 使用 /api/v1/tasks/list 查任务状态
"""

import json
import time
import threading
import sys
import concurrent.futures
from datetime import datetime
from urllib.request import Request, urlopen
from urllib.error import URLError

GW_URL = "http://localhost:8282"
WORKER_ID = "worker-localhost"

results = {
    "start_time": None,
    "end_time": None,
    "total_tasks": 0,
    "completed": 0,
    "failed": 0,
    "total_duration_ms": 0,
    "min_duration_ms": float('inf'),
    "max_duration_ms": 0,
    "errors": [],
    "latency_buckets": {"0-500ms": 0, "500ms-1s": 0, "1s-2s": 0, "2s-5s": 0, "5s-10s": 0, "10s+": 0},
}
results_lock = threading.Lock()
task_ids_created = []
task_ids_lock = threading.Lock()

def api_post(path, data):
    req = Request(f"{GW_URL}{path}", data=json.dumps(data).encode(), method="POST")
    req.add_header("Content-Type", "application/json")
    try:
        with urlopen(req, timeout=60) as resp:
            return json.loads(resp.read())
    except Exception as e:
        return {"success": False, "error": str(e)}

def submit_and_wait(command, timeout_sec=30):
    """
    提交一个任务并等待完成。
    API要求: command 为顶层字段。
    状态通过 list 轮询检查。
    """
    tid = f"stress-{int(time.time()*1000)}-{threading.get_ident()}"
    with task_ids_lock:
        task_ids_created.append(tid)
    
    task_data = {
        "task_id": tid,
        "type": "shell",
        "command": command,
        "target_worker": WORKER_ID,
        "priority": 5
    }
    
    start = time.time()
    
    # 提交
    resp = api_post("/api/v1/tasks/submit", task_data)
    if not resp.get("success"):
        return False, 0, f"提交失败: {resp.get('error', 'unknown')}"
    
    # 轮询 list 查状态
    max_wait = timeout_sec
    poll_interval = 0.5
    waited = 0
    while waited < max_wait:
        time.sleep(poll_interval)
        waited += poll_interval
        
        # 用 list 查
        list_resp = api_post("/api/v1/tasks/list", {"filter": "all"})
        if not list_resp.get("success"):
            # 换 GET
            try:
                req = Request(f"{GW_URL}/api/v1/tasks/list", method="GET")
                with urlopen(req, timeout=5) as r:
                    list_resp = json.loads(r.read())
            except:
                list_resp = {"data": {}}
        
        data_nodes = list_resp.get("data", {})
        if isinstance(data_nodes, list):
            all_tasks = data_nodes
        elif isinstance(data_nodes, dict):
            all_tasks = []
            for tasks in data_nodes.values():
                all_tasks.extend(tasks)
        else:
            all_tasks = []
        
        for t in all_tasks:
            if t.get("task_id") == tid:
                status = t.get("status", "")
                if status == "completed":
                    elapsed = (time.time() - start) * 1000
                    return True, elapsed, None
                elif status in ("failed", "cancelled", "timeout"):
                    elapsed = (time.time() - start) * 1000
                    err = t.get("error", status)
                    return False, elapsed, f"{status}: {err}"
                # 还在运行，继续等
                break
    
    return False, max_wait * 1000, "超时"

def record(success, duration_ms, err=None):
    with results_lock:
        results["total_tasks"] += 1
        if success:
            results["completed"] += 1
        else:
            results["failed"] += 1
            if err:
                results["errors"].append(err)
        
        results["total_duration_ms"] += duration_ms
        results["min_duration_ms"] = min(results["min_duration_ms"], duration_ms)
        results["max_duration_ms"] = max(results["max_duration_ms"], duration_ms)
        
        if duration_ms < 500:
            results["latency_buckets"]["0-500ms"] += 1
        elif duration_ms < 1000:
            results["latency_buckets"]["500ms-1s"] += 1
        elif duration_ms < 2000:
            results["latency_buckets"]["1s-2s"] += 1
        elif duration_ms < 5000:
            results["latency_buckets"]["2s-5s"] += 1
        elif duration_ms < 10000:
            results["latency_buckets"]["5s-10s"] += 1
        else:
            results["latency_buckets"]["10s+"] += 1

def _run(cmd, timeout=10):
    """运行并记录结果"""
    s, d, e = submit_and_wait(cmd, timeout)
    record(s, d, e)
    return s, d, e

def test_basic():
    return _run("echo 'Hello ComputeHub' && hostname && date", 10)

def test_cpu():
    return _run('python3 -c "import math; [math.factorial(i) for i in range(1,2000)]"', 15)

def test_io():
    return _run("dd if=/dev/zero bs=1M count=10 2>/dev/null | md5sum", 15)

def test_sysinfo():
    return _run("free -h && echo '---' && df -h / && echo '---' && uptime", 10)

def test_network():
    return _run("curl -s -o /dev/null -w '%{http_code} %{time_total}s' https://httpbin.org/get", 15)

def test_long():
    return _run("echo 'Start...' && sleep 3 && echo 'Mid...' && sleep 3 && echo 'Done!'", 30)

def test_error():
    return _run("exit 42", 5)

def run_stress_phase(name, test_fn, concurrency, count):
    print(f"\n{'='*60}")
    print(f"📊 阶段: {name}")
    print(f"    并发={concurrency}  任务数={count}")
    print(f"{'='*60}")
    
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as ex:
        futures = [ex.submit(test_fn) for _ in range(count)]
        done = 0
        for f in concurrent.futures.as_completed(futures):
            done += 1
            s, d, e = f.result()
            mark = "✅" if s else "❌"
            sys.stdout.write(f"\r  {done}/{count} {mark} {d:.0f}ms    ")
            sys.stdout.flush()
    
    elapsed = time.time() - start
    print(f"\n  耗时={elapsed:.1f}s  吞吐={count/elapsed:.1f}/s")
    print_status()

def print_status():
    with results_lock:
        c, f, t = results["completed"], results["failed"], results["total_tasks"]
        avg = results["total_duration_ms"] / t if t else 0
        print(f"  ➡  ✅{c} ❌{f} | avg={avg:.0f}ms min={results['min_duration_ms']:.0f}ms max={results['max_duration_ms']:.0f}ms")

def print_report():
    print("\n\n" + "="*60)
    print("📋 压测报告")
    print("="*60)
    
    with results_lock:
        r = results
        t = r["total_tasks"]
        if not t:
            print("没有任务被执行")
            return
        
        sr = r["completed"] / t * 100
        avg = r["total_duration_ms"] / t
        print(f"\n📊 总览")
        print(f"  总任务: {t}")
        print(f"  完成:  {r['completed']} ({sr:.1f}%)")
        print(f"  失败:  {r['failed']} ({100-sr:.1f}%)")
        print(f"\n⏱ 延迟")
        print(f"  平均: {avg:.0f}ms")
        print(f"  最小: {r['min_duration_ms']:.0f}ms")
        print(f"  最大: {r['max_duration_ms']:.0f}ms")
        print(f"\n📈 分布")
        for b, c in r["latency_buckets"].items():
            bar = "█" * int(c / max(1, max(r["latency_buckets"].values())) * 30)
            print(f"  {b:>12}: {c:>4} ({c/t*100:5.1f}%) {bar}")
        
        if r["errors"]:
            print(f"\n⚠ 错误(前5):")
            for e in r["errors"][:5]:
                print(f"  {e}")

def main():
    print("🚀 ComputeHub Worker 压力测试 v2")
    print(f"  Gateway: {GW_URL}")
    print(f"  Worker:  {WORKER_ID}")
    print(f"  时间:    {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # 先跑一个验证
    print("🔍 验证通信...")
    s, d, e = submit_and_wait("echo 'pong'", 5)
    print(f"  {'✅' if s else '❌'} ({d:.0f}ms) {e or ''}")
    if not s:
        print("  ❌ 通信验证失败，停止测试")
        return
    print()
    
    with results_lock:
        results["start_time"] = time.time()
    
    # === 阶段1: 基础功能 ===
    print("📋 基础功能测试")
    for name, fn in [("基础命令", test_basic), ("CPU计算", test_cpu), ("IO读写", test_io), ("系统信息", test_sysinfo)]:
        s, d, e = fn()
        print(f"  {name}: {'✅' if s else '❌'} ({d:.0f}ms)")
    
    # === 阶段2-6: 压力阶段 ===
    run_stress_phase("低并发 5×20", test_basic, 5, 20)
    run_stress_phase("中并发 10×40", test_sysinfo, 10, 40)
    
    # 混合
    print(f"\n{'='*60}")
    print("📊 阶段: 混合任务 10×30")
    print(f"{'='*60}")
    mix = [test_cpu, test_io, test_basic, test_sysinfo, test_network]
    start = time.time()
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as ex:
        futures = [ex.submit(mix[i % len(mix)]) for i in range(30)]
        done = 0
        for f in concurrent.futures.as_completed(futures):
            done += 1
            s, d, e = f.result()
            sys.stdout.write(f"\r  {done}/30 {'✅' if s else '❌'} {d:.0f}ms    ")
            sys.stdout.flush()
    print(f"\n  耗时={time.time()-start:.1f}s")
    print_status()
    
    run_stress_phase("高并发 20×30", test_basic, 20, 30)
    run_stress_phase("长短混合 5×15", lambda: test_long() if id(threading.current_thread()) % 3 == 0 else test_basic(), 5, 15)
    run_stress_phase("错误注入 10×10", test_error, 10, 10)
    
    with results_lock:
        results["end_time"] = time.time()
    
    print_report()
    
    ts = datetime.now().strftime('%Y%m%d_%H%M%S')
    rp = f"/root/.openclaw/workspace/ai_agent/results/stress_test_{ts}.json"
    with open(rp, "w") as f:
        with results_lock:
            rep = dict(results)
        rep["errors"] = rep["errors"][:20]
        json.dump(rep, f, indent=2, ensure_ascii=False)
    print(f"\n📁 报告: {rp}")

if __name__ == "__main__":
    main()
