#!/usr/bin/env python3
"""
ComputeHub worker-localhost 压力测试
目标: 测试本地 gateway (localhost:8282) 在 worker-localhost 上的并发处理能力
"""

import json
import time
import sys
import os
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed

API_BASE = "http://localhost:8282"
API_KEY = ""  # 本地不需要 key

HEADER = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json",
}

results = []
test_config = {
    "target_node": "worker-localhost",
    "total_tasks": 50,
    "concurrency": 10,
}

def submit_task(task_id, command, priority=5, timeout=60):
    """提交任务到 gateway"""
    url = f"{API_BASE}/api/v1/tasks/submit"
    payload = {
        "task_id": task_id,
        "command": command,
        "assigned_node": "worker-localhost",
        "priority": priority,
        "timeout": timeout,
    }
    
    start = time.time()
    try:
        import http.client
        from urllib.parse import urlparse
        
        parsed = urlparse(url)
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=10)
        conn.request("POST", parsed.path, body=json.dumps(payload), headers=HEADER)
        resp = conn.getresponse()
        data = resp.read().decode()
        elapsed = time.time() - start
        
        result = json.loads(data)
        
        return {
            "task_id": task_id,
            "status": "submitted" if result.get("success") else f"FAIL_{resp.status}",
            "duration_ms": round(elapsed * 1000, 2),
            "response_time": round(elapsed, 3),
            "gateway_response": data[:200],
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "task_id": task_id,
            "status": f"EXCEPTION_{str(e)[:50]}",
            "duration_ms": round(elapsed * 1000, 2),
            "response_time": round(elapsed, 3),
            "gateway_response": str(e),
        }


def poll_task_result(task_id, max_wait=30, poll_interval=0.5):
    """轮询任务结果"""
    url = f"{API_BASE}/api/v1/tasks/detail?task_id={task_id}"
    
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > max_wait:
            return {
                "task_id": task_id,
                "status": "timeout",
                "total_duration_s": round(elapsed, 2),
            }
        
        try:
            import http.client
            from urllib.parse import urlparse
            
            parsed = urlparse(url)
            conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
            conn.request("GET", parsed.path)
            resp = conn.getresponse()
            data = resp.read().decode()
            result = json.loads(data)
            
            task_data = result.get("data", {})
            task_status = task_data.get("status", "")
            
            if task_status in ["completed", "failed", "cancelled", "preempted"]:
                duration = task_data.get("duration", "unknown")
                exit_code = task_data.get("exit_code", -1)
                success = task_data.get("success", False)
                
                return {
                    "task_id": task_id,
                    "status": "completed" if success else f"failed(code={exit_code})",
                    "total_duration_s": round(elapsed, 2),
                    "task_duration": duration,
                    "exit_code": exit_code,
                }
            
            time.sleep(poll_interval)
        except Exception as e:
            time.sleep(poll_interval)


def check_node_status():
    """获取节点当前状态"""
    try:
        import http.client
        parsed = urlparse(f"{API_BASE}/api/v1/nodes/list")
        conn = http.client.HTTPConnection(parsed.hostname, parsed.port, timeout=5)
        conn.request("GET", parsed.path)
        resp = conn.getresponse()
        data = json.loads(resp.read().decode())
        nodes = data.get("data", [])
        
        for node in nodes:
            if node.get("node_id") == "worker-localhost":
                return {
                    "node_id": node["node_id"],
                    "status": node["status"],
                    "active_tasks": node["active_tasks"],
                    "region": node["region"],
                }
    except:
        return {"node_id": "worker-localhost", "error": "无法获取节点状态"}
    
    return {"node_id": "worker-localhost", "error": "未找到节点"}


print("╔══════════════════════════════════════════════════════════════╗")
print("║              ComputeHub Worker 压力测试                     ║")
print(f"║  测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print("╚══════════════════════════════════════════════════════════════╝")

# ==================== 阶段 1: 节点确认 ====================
print("\n" + "═"*70)
print("阶段 1/3: 节点确认")
print("═"*70)
node_info = check_node_status()
print(f"📍 节点: {node_info}")

# ==================== 阶段 2: 快速命令并发测试 ====================
print("\n" + "═"*70)
print("阶段 2/3: 快速命令并发测试 (echo 类)")
print("═"*70)

total_tasks = 30
batch_size = 10
success_count = 0
fail_count = 0

start_batch = time.time()
print(f"📊 提交 {total_tasks} 个 echo 任务，并发度 {batch_size}...")

with ThreadPoolExecutor(max_workers=batch_size) as executor:
    futures = []
    for i in range(total_tasks):
        cmd = f"echo 'task-{i+1}'; nproc; free -m | head -2"
        future = executor.submit(submit_task, f"stress-echo-{i+1:03d}", cmd, priority=5)
        futures.append(future)
    
    for future in as_completed(futures):
        result = future.result()
        results.append(result)
        if result["status"] == "submitted":
            success_count += 1
        else:
            fail_count += 1

submit_time = time.time() - start_batch
print(f"📤 提交完成: 成功 {success_count}/{total_tasks}, 失败 {fail_count}/{total_tasks}")
print(f"⏱ 总提交耗时: {submit_time:.2f}s")
print(f"⚡ 平均提交速度: {submit_time/total_tasks*1000:.1f}ms/任务")

# 查看节点状态
node_after_submit = check_node_status()
print(f"📊 提交后节点状态: 活跃任务数={node_after_submit.get('active_tasks', 'N/A')}")

# ==================== 阶段 3: 结果轮询 ====================
print("\n" + "═"*70)
print("阶段 3/3: 结果轮询与统计")
print("═"*70)

completed_tasks = 0
failed_tasks = 0
timeout_tasks = 0
task_durations = []

print("🔍 开始轮询任务结果...")
poll_start = time.time()

with ThreadPoolExecutor(max_workers=20) as executor:
    future_map = {}
    for result in results:
        if result["status"] == "submitted":
            future = executor.submit(poll_task_result, result["task_id"])
            future_map[future] = result["task_id"]
    
    for future in as_completed(future_map):
        task_id = future_map[future]
        result = future.result()
        
        results.append(result)
        if result["status"] == "completed":
            completed_tasks += 1
            try:
                task_durations.append(float(result.get("total_duration_s", 0)))
            except:
                pass
        elif result["status"].startswith("failed"):
            failed_tasks += 1
        elif result["status"] == "timeout":
            timeout_tasks += 1
        
        if (completed_tasks + failed_tasks + timeout_tasks) % 10 == 0:
            print(f"   进度: {completed_tasks + failed_tasks + timeout_tasks}/{total_tasks}")

poll_time = time.time() - poll_start
print(f"📋 轮询完成: 成功={completed_tasks}, 失败={failed_tasks}, 超时={timeout_tasks}")
print(f"⏱ 轮询总耗时: {poll_time:.2f}s")

# ==================== 最终统计 ====================
print("\n" + "═"*70)
print("📊 最终统计报告")
print("═"*70)

if task_durations:
    avg_duration = sum(task_durations) / len(task_durations)
    min_duration = min(task_durations)
    max_duration = max(task_durations)
    print(f"⏱ 任务执行时间:")
    print(f"   平均: {avg_duration:.2f}s")
    print(f"   最快: {min_duration:.2f}s")
    print(f"   最慢: {max_duration:.2f}s")

total_time = time.time() - start_batch
print(f"\n⏱ 总测试时间: {total_time:.2f}s")
print(f"📈 吞吐量: {total_tasks/total_time:.1f} 任务/秒")
print(f"✅ 成功率: {completed_tasks}/{total_tasks} ({completed_tasks/total_tasks*100:.1f}%)")

print(f"\n📊 提交分析:")
submit_durations = [r["duration_ms"] for r in results if "duration_ms" in r]
if submit_durations:
    print(f"   提交延迟: 平均={sum(submit_durations)/len(submit_durations):.1f}ms, "
          f"最快={min(submit_durations):.1f}ms, 最慢={max(submit_durations):.1f}ms")

# 最终节点状态
final_node = check_node_status()
print(f"\n📊 最终节点状态:")
print(f"   节点: {final_node}")

# ==================== 生成详细报告 ====================
report = {
    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    "test_name": "worker-localhost 压力测试",
    "config": {
        "target_node": "worker-localhost",
        "total_tasks": total_tasks,
        "batch_size": batch_size,
    },
    "summary": {
        "total_tasks": total_tasks,
        "success": completed_tasks,
        "failed": failed_tasks,
        "timeout": timeout_tasks,
        "success_rate_pct": round(completed_tasks/total_tasks*100, 1),
        "submit_time_s": round(submit_time, 2),
        "poll_time_s": round(poll_time, 2),
        "total_time_s": round(total_time, 2),
        "throughput": round(total_tasks/total_time, 1),
        "avg_submit_latency_ms": round(sum(submit_durations)/len(submit_durations), 1) if submit_durations else 0,
    },
    "task_durations": {
        "avg_s": round(avg_duration, 2) if task_durations else None,
        "min_s": round(min_duration, 2) if task_durations else None,
        "max_s": round(max_duration, 2) if task_durations else None,
        "count": len(task_durations),
    },
    "details": results,
    "node_state": final_node,
}

report_path = "/root/.openclaw/workspace/ai_agent/results/worker_stress_test_report.json"
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print(f"\n📄 完整报告: {report_path}")

# ==================== 额外测试: 持续压力 ====================
print("\n" + "═"*70)
print("🔥 额外测试: 持续压力 (20s 持续提交)")
print("═"*70)

burst_start = time.time()
burst_count = 0
burst_success = 0
burst_fail = 0

while time.time() - burst_start < 20:  # 持续 20 秒
    try:
        task_id = f"burst-{int(burst_start * 1000)}-{burst_count}"
        result = submit_task(task_id, f"echo '{task_id}'; date", priority=1)
        burst_count += 1
        if result["status"] == "submitted":
            burst_success += 1
        else:
            burst_fail += 1
    except Exception as e:
        burst_count += 1
        burst_fail += 1
        print(f"  💥 Burst 失败: {e}")

burst_time = time.time() - burst_start
print(f"🔥 20秒持续提交:")
print(f"   总提交: {burst_count} 个")
print(f"   成功: {burst_success} 个")
print(f"   失败: {burst_fail} 个")
print(f"   平均: {burst_count/burst_time:.1f} 任务/秒")

# 保存 burst 结果
report["burst_test"] = {
    "duration_s": round(burst_time, 1),
    "total_submitted": burst_count,
    "successful": burst_success,
    "failed": burst_fail,
    "throughput": round(burst_count/burst_time, 1) if burst_time > 0 else 0,
}

with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, indent=2, ensure_ascii=False)

print("\n" + "╔" + "═"*68 + "╗")
print("║                 🎯 测试完成                                ║")
print("╚" + "═"*68 + "╝")
