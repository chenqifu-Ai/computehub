#!/usr/bin/env python3
"""
Week 5 Day 1: 性能测试
执行者：小智 AI 助手
时间：2026-04-22 18:13
"""

import os
import sys
import time
import requests
import statistics
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime
from pathlib import Path

# === 配置 ===
BASE_URL = "http://localhost:8080"
REPORT_DIR = Path("/root/.openclaw/workspace/ai_agent/code/computehub/orchestration/go/reports")

# === 颜色输出 ===
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    RESET = '\033[0m'

def log(msg, level="INFO"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    colors = {"INFO": Colors.BLUE, "SUCCESS": Colors.GREEN, "WARNING": Colors.YELLOW, 
              "ERROR": Colors.RED, "TEST": Colors.CYAN}
    color = colors.get(level, Colors.RESET)
    print(f"{color}[{timestamp}] [{level}] {msg}{Colors.RESET}")

def single_request(endpoint, method="GET", data=None):
    """单次请求"""
    try:
        start = time.time()
        if method == "GET":
            resp = requests.get(f"{BASE_URL}{endpoint}", timeout=10)
        elif method == "POST":
            resp = requests.post(f"{BASE_URL}{endpoint}", json=data, timeout=10)
        else:
            resp = requests.request(method, f"{BASE_URL}{endpoint}", json=data, timeout=10)
        elapsed = (time.time() - start) * 1000  # ms
        return {
            "status": resp.status_code,
            "elapsed": elapsed,
            "success": resp.status_code == 200
        }
    except Exception as e:
        return {
            "status": 0,
            "elapsed": 0,
            "success": False,
            "error": str(e)
        }

def concurrent_requests(endpoint, method="GET", data=None, concurrency=10, total_requests=100):
    """并发请求测试"""
    log(f"并发测试：{endpoint} (并发={concurrency}, 总数={total_requests})", "TEST")
    
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(single_request, endpoint, method, data) for _ in range(total_requests)]
        for future in as_completed(futures):
            results.append(future.result())
    
    total_time = time.time() - start_time
    
    # 统计分析
    successful = [r for r in results if r["success"]]
    failed = [r for r in results if not r["success"]]
    latencies = [r["elapsed"] for r in successful]
    
    if not latencies:
        return {
            "success_rate": 0,
            "qps": 0,
            "avg_latency": 0,
            "p50_latency": 0,
            "p95_latency": 0,
            "p99_latency": 0,
            "failed": len(failed)
        }
    
    return {
        "total_requests": total_requests,
        "successful": len(successful),
        "failed": len(failed),
        "success_rate": len(successful) / total_requests * 100,
        "total_time": total_time,
        "qps": total_requests / total_time,
        "avg_latency": statistics.mean(latencies),
        "min_latency": min(latencies),
        "max_latency": max(latencies),
        "p50_latency": statistics.median(latencies),
        "p95_latency": sorted(latencies)[int(len(latencies) * 0.95)] if len(latencies) > 1 else latencies[0],
        "p99_latency": sorted(latencies)[int(len(latencies) * 0.99)] if len(latencies) > 1 else latencies[0],
    }

def test_health_endpoint():
    """健康检查端点测试"""
    log("=" * 70, "INFO")
    log("测试 1: 健康检查端点 (/api/health)", "TEST")
    log("=" * 70, "INFO")
    
    # 单次测试
    result = single_request("/api/health")
    log(f"  单次请求：{result['elapsed']:.2f}ms (状态码：{result['status']})", "SUCCESS" if result["success"] else "ERROR")
    
    # 并发测试
    stats = concurrent_requests("/api/health", concurrency=20, total_requests=200)
    
    log(f"  成功率：{stats['success_rate']:.1f}%", "SUCCESS" if stats['success_rate'] > 99 else "WARNING")
    log(f"  QPS: {stats['qps']:.1f}", "SUCCESS")
    log(f"  平均延迟：{stats['avg_latency']:.2f}ms", "SUCCESS")
    log(f"  P50 延迟：{stats['p50_latency']:.2f}ms", "SUCCESS")
    log(f"  P95 延迟：{stats['p95_latency']:.2f}ms", "SUCCESS")
    log(f"  P99 延迟：{stats['p99_latency']:.2f}ms", "SUCCESS")
    
    return {"health": stats}

def test_storage_endpoints():
    """存储端点测试"""
    log("", "INFO")
    log("=" * 70, "INFO")
    log("测试 2: 存储端点 (/api/storage/*)", "TEST")
    log("=" * 70, "INFO")
    
    results = {}
    
    # 保存任务
    log("  测试：POST /api/storage/tasks", "TEST")
    for i in range(10):
        task_data = {
            "task_id": f"perf-test-{i}",
            "data": {"name": f"性能测试任务{i}", "framework": "pytorch", "gpu_count": 4}
        }
        result = single_request("/api/storage/tasks", "POST", task_data)
        if result["success"]:
            log(f"    ✅ 任务{i} 保存成功 ({result['elapsed']:.2f}ms)", "SUCCESS")
        else:
            log(f"    ❌ 任务{i} 保存失败", "ERROR")
    
    # 列出任务
    log("  测试：GET /api/storage/tasks", "TEST")
    stats = concurrent_requests("/api/storage/tasks", concurrency=10, total_requests=50)
    log(f"    成功率：{stats['success_rate']:.1f}%", "SUCCESS" if stats['success_rate'] > 99 else "WARNING")
    log(f"    QPS: {stats['qps']:.1f}", "SUCCESS")
    log(f"    平均延迟：{stats['avg_latency']:.2f}ms", "SUCCESS")
    
    results["storage"] = stats
    return results

def test_scheduler_endpoints():
    """调度器端点测试"""
    log("", "INFO")
    log("=" * 70, "INFO")
    log("测试 3: 调度器端点 (/api/scheduler/*)", "TEST")
    log("=" * 70, "INFO")
    
    # 获取节点列表
    log("  测试：GET /api/scheduler/nodes", "TEST")
    stats = concurrent_requests("/api/scheduler/nodes", concurrency=10, total_requests=50)
    log(f"    成功率：{stats['success_rate']:.1f}%", "SUCCESS" if stats['success_rate'] > 99 else "WARNING")
    log(f"    QPS: {stats['qps']:.1f}", "SUCCESS")
    log(f"    平均延迟：{stats['avg_latency']:.2f}ms", "SUCCESS")
    
    return {"scheduler": stats}

def test_streaming_endpoints():
    """流式端点测试"""
    log("", "INFO")
    log("=" * 70, "INFO")
    log("测试 4: 流式端点 (/api/stream/stats)", "TEST")
    log("=" * 70, "INFO")
    
    # 流状态查询
    log("  测试：GET /api/stream/stats", "TEST")
    stats = concurrent_requests("/api/stream/stats", concurrency=10, total_requests=50)
    log(f"    成功率：{stats['success_rate']:.1f}%", "SUCCESS" if stats['success_rate'] > 99 else "WARNING")
    log(f"    QPS: {stats['qps']:.1f}", "SUCCESS")
    log(f"    平均延迟：{stats['avg_latency']:.2f}ms", "SUCCESS")
    
    return {"streaming": stats}

def generate_report(all_results):
    """生成性能测试报告"""
    log("", "INFO")
    log("=" * 70, "INFO")
    log("生成性能测试报告", "TEST")
    log("=" * 70, "INFO")
    
    REPORT_DIR.mkdir(parents=True, exist_ok=True)
    report_path = REPORT_DIR / "performance_test_report.md"
    
    report = f"""# 🚀 ComputeHub 性能测试报告

**测试时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**测试工具**: Python + requests + ThreadPoolExecutor  
**测试环境**: localhost:8080  
**版本**: orchestrator-v8

---

## 📊 总体结果

| 端点 | QPS | 平均延迟 | P50 延迟 | P95 延迟 | P99 延迟 | 成功率 |
|------|-----|----------|----------|----------|----------|--------|
"""
    
    for test_name, stats in all_results.items():
        if isinstance(stats, dict) and "qps" in stats:
            report += f"| {test_name} | {stats.get('qps', 0):.1f} | {stats.get('avg_latency', 0):.2f}ms | {stats.get('p50_latency', 0):.2f}ms | {stats.get('p95_latency', 0):.2f}ms | {stats.get('p99_latency', 0):.2f}ms | {stats.get('success_rate', 0):.1f}% |\n"
    
    report += f"""
---

## 📈 性能指标

### 健康检查端点
- **QPS**: {all_results.get('health', {}).get('qps', 0):.1f}
- **平均延迟**: {all_results.get('health', {}).get('avg_latency', 0):.2f}ms
- **P95 延迟**: {all_results.get('health', {}).get('p95_latency', 0):.2f}ms
- **成功率**: {all_results.get('health', {}).get('success_rate', 0):.1f}%

---

## 🎯 性能目标

| 指标 | 目标 | 实际 | 状态 |
|------|------|------|------|
| QPS | >1000 | {all_results.get('health', {}).get('qps', 0):.1f} | {"✅" if all_results.get('health', {}).get('qps', 0) > 1000 else "⚠️"} |
| 平均延迟 | <10ms | {all_results.get('health', {}).get('avg_latency', 0):.2f}ms | {"✅" if all_results.get('health', {}).get('avg_latency', 0) < 10 else "⚠️"} |
| P95 延迟 | <50ms | {all_results.get('health', {}).get('p95_latency', 0):.2f}ms | {"✅" if all_results.get('health', {}).get('p95_latency', 0) < 50 else "⚠️"} |
| 成功率 | >99% | {all_results.get('health', {}).get('success_rate', 0):.1f}% | {"✅" if all_results.get('health', {}).get('success_rate', 0) > 99 else "⚠️"} |

---

## 💡 优化建议

"""
    
    if all_results.get('health', {}).get('avg_latency', 0) > 10:
        report += "1. ⚠️ 平均延迟偏高，建议优化 HTTP 处理逻辑\n"
    if all_results.get('health', {}).get('qps', 0) < 1000:
        report += "2. ⚠️ QPS 未达目标，建议进行并发优化\n"
    if all_results.get('health', {}).get('success_rate', 0) < 99:
        report += "3. ⚠️ 成功率偏低，建议检查错误处理\n"
    
    report += f"""
---

## 📝 测试说明

- **并发数**: 10-20
- **总请求数**: 50-200  per 端点
- **超时时间**: 10 秒
- **测试方法**: Python ThreadPoolExecutor

---

**报告生成时间**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}  
**执行者**: 小智 AI 助手
"""
    
    report_path.write_text(report, encoding='utf-8')
    log(f"  ✅ 报告已保存：{report_path}", "SUCCESS")
    
    return report_path

def run_all_tests():
    """运行所有测试"""
    log("=" * 70, "INFO")
    log("Week 5 Day 1: 性能测试启动", "INFO")
    log("=" * 70, "INFO")
    
    all_results = {}
    
    try:
        # 测试健康检查
        all_results["health"] = test_health_endpoint()["health"]
        
        # 测试存储端点
        all_results["storage"] = test_storage_endpoints()["storage"]
        
        # 测试调度器端点
        all_results["scheduler"] = test_scheduler_endpoints()["scheduler"]
        
        # 测试流式端点
        all_results["streaming"] = test_streaming_endpoints()["streaming"]
        
        # 生成报告
        report_path = generate_report(all_results)
        
        log("", "INFO")
        log("=" * 70, "INFO")
        log("✅ 性能测试完成！", "SUCCESS")
        log(f"📄 报告：{report_path}", "SUCCESS")
        log("=" * 70, "INFO")
        
        return True
    except Exception as e:
        log(f"❌ 测试失败：{e}", "ERROR")
        return False

if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
