#!/usr/bin/env python3
"""
ComputeHub 压力测试脚本
测试项目:
  1. 高并发提交 — 批量快速提交任务
  2. 执行能力 — CPU/IO/内存密集型任务
  3. 持久性 — 长时间运行的任务
  4. 大负载 — 大量输出
  5. 边缘情况 — 空命令、超长命令、特殊字符
  6. 流式反馈 — 验证 progress 接口
"""

import json
import re
import time
import urllib.request
import concurrent.futures
from collections import defaultdict

BASE = "http://127.0.0.1:8282"
NODE = "fedora-vm-01"

def clean_ansi(s):
    return re.sub(r'\x1b\[[0-9;]*[a-zA-Z]', '', s)

def submit_task(task_id, command, timeout=30):
    """提交单个任务"""
    url = f"{BASE}/api/v1/tasks/submit"
    body = json.dumps({
        "task_id": task_id,
        "command": command,
        "timeout": timeout
    }).encode()
    req = urllib.request.Request(url, data=body, headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(clean_ansi(resp.read().decode()))
            return data.get("success", False)
    except Exception as e:
        return False

def get_task_detail(task_id):
    """获取任务详情"""
    url = f"{BASE}/api/v1/tasks/detail?task_id={task_id}&node_id={NODE}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = clean_ansi(resp.read().decode())
            data = json.loads(raw)
            d = data.get("data", {})
            return {
                "status": d.get("status", "UNKNOWN"),
                "success": d.get("success"),
                "exit_code": d.get("exit_code"),
                "duration": d.get("duration", ""),
                "stdout": clean_ansi(d.get("stdout", "")),
                "stderr": clean_ansi(d.get("stderr", "")),
                "error": d.get("error", ""),
            }
    except Exception as e:
        return {"status": "ERROR", "error": str(e)}

def get_progress(task_id):
    """获取任务进度"""
    url = f"{BASE}/api/v1/tasks/progress?task_id={task_id}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw = clean_ansi(resp.read().decode())
            data = json.loads(raw)
            return data.get("data", {})
    except:
        return {}


def wait_for_completion(task_ids, timeout=60, interval=1):
    """等待一批任务完成"""
    results = {}
    deadline = time.time() + timeout
    start = time.time()
    all_done = False
    
    while time.time() < deadline and not all_done:
        all_done = True
        for tid in task_ids:
            if tid not in results:
                results[tid] = get_task_detail(tid)
            if results[tid]["status"] not in ("completed",):
                all_done = False
        if all_done:
            break
        time.sleep(interval)
    
    # 填充剩余未完成的
    for tid in task_ids:
        if tid not in results:
            results[tid] = get_task_detail(tid)
    
    elapsed = time.time() - start
    return results, elapsed

def run_stress_tests():
    print("=" * 70)
    print("  🔥 ComputeHub 全功能压力测试")
    print("=" * 70)
    print()
    
    results = defaultdict(list)
    total_start = time.time()
    
    # ============================================================
    # 测试 1: 高并发快速提交 (100 个轻量任务)
    # ============================================================
    print("📌 测试 1: 高并发快速提交 (100 x echo)")
    print("-" * 50)
    t1_start = time.time()
    task_ids_1 = [f"stress-1-{i:04d}" for i in range(100)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=20) as pool:
        futures = [
            pool.submit(submit_task, tid, f"echo stress1-{i}")
            for i, tid in enumerate(task_ids_1)
        ]
        submit_ok = sum(1 for f in concurrent.futures.as_completed(futures) if f.result())
    
    t1_duration = time.time() - t1_start
    print(f"  提交: {submit_ok}/100 ({t1_duration:.2f}s, 并行度 20)")
    results["submit"].append(submit_ok)
    
    # 等待完成
    t1_results, t1_wait = wait_for_completion(task_ids_1, timeout=30)
    t1_success = sum(1 for r in t1_results.values() if r["success"])
    print(f"  完成: {t1_success}/100 (等待 {t1_wait:.2f}s)")
    results["complete"].append(t1_success)
    
    t1_total = time.time() - t1_start
    throughput = 100 / t1_total if t1_total > 0 else 0
    print(f"  吞吐量: {throughput:.1f} tasks/s")
    print(f"  ✅ 测试 1 完成\n")
    
    # ============================================================
    # 测试 2: 中等并发 (50 个 Python 计算任务)
    # ============================================================
    print("📌 测试 2: Python 计算负载 (50 x 计算密集型)")
    print("-" * 50)
    t2_start = time.time()
    task_ids_2 = [f"stress-2-{i:04d}" for i in range(50)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=10) as pool:
        futures = [
            pool.submit(submit_task, tid, 
                f"echo calc-{i} && python3 -c \"s=0\\nfor i in range({500000+i}): s+=i\\nprint(s)\"")
            for i, tid in enumerate(task_ids_2)
        ]
        submit_ok_2 = sum(1 for f in concurrent.futures.as_completed(futures) if f.result())
    
    print(f"  提交: {submit_ok_2}/50 ({time.time()-t2_start:.2f}s)")
    results["submit"].append(submit_ok_2)
    
    t2_results, t2_wait = wait_for_completion(task_ids_2, timeout=60)
    t2_success = sum(1 for r in t2_results.values() if r["success"])
    t2_avg = sum(float(get_duration(r["duration"])) for r in t2_results.values()) / max(len(t2_results), 1)
    print(f"  完成: {t2_success}/50 (平均 {t2_avg:.0f}ms)")
    results["complete"].append(t2_success)
    print(f"  ✅ 测试 2 完成\n")
    
    # ============================================================
    # 测试 3: 超大输出任务
    # ============================================================
    print("📌 测试 3: 大输出任务 (生成 1000 行数据)")
    print("-" * 50)
    t3_start = time.time()
    task_ids_3 = ["stress-3-largeout"]
    
    submit_task("stress-3-largeout", 
        "echo large-output-start && python3 -c \"\\nfor i in range(1000): print(f'line-{i}: data-{i*7+i}')\" && echo large-output-end")
    
    t3_results, t3_wait = wait_for_completion(task_ids_3, timeout=30)
    r = t3_results.get("stress-3-largeout", {})
    if r["success"]:
        stdout = r["stdout"]
        line_count = stdout.count("\n")
        size = len(stdout)
        print(f"  输出行数: {line_count}")
        print(f"  输出大小: {size} bytes ({size/1024:.1f} KB)")
        print(f"  前3行: {stdout.split(chr(10))[:3]}")
        print(f"  耗时: {t3_wait:.2f}s")
    else:
        print(f"  ❌ 失败: {r}")
    print(f"  ✅ 测试 3 完成\n")
    
    # ============================================================
    # 测试 4: 持久性 — 长时间运行任务
    # ============================================================
    print("📌 测试 4: 长时间运行任务 (sleep 30)")
    print("-" * 50)
    t4_start = time.time()
    task_ids_4 = ["stress-4-long"]
    
    submit_task("stress-4-long", "echo start && sleep 15 && echo done", timeout=60)
    
    # 在任务运行时检查进度
    for _ in range(5):
        time.sleep(3)
        progress = get_progress("stress-4-long")
        if progress:
            print(f"  进度检查: {json.dumps(progress, indent=None)}")
    
    t4_results, t4_wait = wait_for_completion(task_ids_4, timeout=60)
    r = t4_results.get("stress-4-long", {})
    print(f"  状态: {r['status']}, 成功: {r['success']}, 耗时: {t4_wait:.2f}s")
    results["long_running"].append(r["success"])
    print(f"  ✅ 测试 4 完成\n")
    
    # ============================================================
    # 测试 5: 边缘情况
    # ============================================================
    print("📌 测试 5: 边缘情况")
    print("-" * 50)
    edge_cases = [
        ("stress-5-empty", "echo ''", True, "空输出"),
        ("stress-5-special", 'echo "hello\\nworld\\ttab\\t$HOME"', True, "特殊字符"),
        ("stress-5-chinese", "echo '你好世界测试压力测试中文'", True, "中文字符"),
        ("stress-5-longcmd", "seq 1 100 | tr '\\n' ',' | rev", True, "管道链"),
        ("stress-5-unicode", "echo '🔥💯✅🎉'", True, "Emoji"),
    ]
    
    for tid, cmd, expected, desc in edge_cases:
        ok = submit_task(tid, cmd)
        if ok:
            r = get_task_detail(tid)
            status = "✅" if r["success"] == expected else "❌"
            print(f"  {status} {desc:15s} | exit={r['exit_code']} | {r['stdout'][:60]}")
            results["edge"].append(r["success"] == expected)
        else:
            print(f"  ❌ {desc:15s} | 提交失败")
            results["edge"].append(False)
    print(f"  ✅ 测试 5 完成\n")
    
    # ============================================================
    # 测试 6: 快速提交-快速完成 (小任务批量)
    # ============================================================
    print("📌 测试 6: 快速批次 (200 x sleep 1)")
    print("-" * 50)
    t6_start = time.time()
    task_ids_6 = [f"stress-6-{i:04d}" for i in range(200)]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=30) as pool:
        futures = [
            pool.submit(submit_task, tid, f"echo batch-{i}")
            for i, tid in enumerate(task_ids_6)
        ]
        submit_ok_6 = sum(1 for f in concurrent.futures.as_completed(futures) if f.result())
    
    print(f"  提交: {submit_ok_6}/200 ({time.time()-t6_start:.2f}s)")
    results["submit"].append(submit_ok_6)
    
    t6_results, t6_wait = wait_for_completion(task_ids_6, timeout=60)
    t6_success = sum(1 for r in t6_results.values() if r["success"])
    print(f"  完成: {t6_success}/200 (等待 {t6_wait:.2f}s)")
    results["complete"].append(t6_success)
    print(f"  ✅ 测试 6 完成\n")
    
    # ============================================================
    # 汇总
    # ============================================================
    total_elapsed = time.time() - total_start
    print("=" * 70)
    print("  📊 压力测试汇总")
    print("=" * 70)
    print(f"  总耗时: {total_elapsed:.2f}s")
    print()
    print("  提交成功率: {}/{} ({:.1f}%)".format(
        sum(results["submit"]), len(results["submit"]) * 100 + 250,
        sum(results["submit"]) / (sum(results["submit"]) + len(results["submit"]) * 0) * 100 if results["submit"] else 0
    ))
    
    total_submitted = 100 + 50 + 1 + 1 + 5 + 200
    total_completed = sum(results["complete"])
    edge_pass = sum(results.get("edge", []))
    edge_total = len(results.get("edge", []))
    long_ok = sum(results.get("long_running", []))
    
    print(f"  总提交:  {total_submitted} 个任务")
    print(f"  总完成:  {total_completed} + 1(长运行) = {total_completed + 1}")
    print(f"  边缘测试: {edge_pass}/{edge_total}")
    print(f"  长运行:  {'✅' if long_ok else '❌'}")
    print(f"  整体吞吐量: {total_submitted / total_elapsed:.1f} tasks/s")
    print()
    
    if total_completed >= total_submitted - 2 and edge_pass == edge_total:
        print("  🎉 全部通过！ComputeHub 扛住了压力测试！")
    else:
        print(f"  ⚠️ 有部分任务未完成 ({total_submitted - total_completed} 个)")
    print("=" * 70)


def get_duration(s):
    try:
        return float(s.replace("ms", "").replace("s", ""))
    except:
        return 0

if __name__ == "__main__":
    run_stress_tests()
