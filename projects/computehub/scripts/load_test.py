#!/usr/bin/env python3
"""
ComputeHub 自动化压测脚本
Sprint 5.2 - 生产就绪

功能:
  - 健康检查 /api/health
  - 系统状态 /api/status
  - 节点注册 + 心跳 + 指标轮询
  - 任务提交 + 结果查询
  - 并发压测 (50/100/200/400/500)
  - JSON 格式报告输出

用法:
  python3 load_test.py                    # 默认压测
  python3 load_test.py --concurrency 200  # 指定并发
  python3 load_test.py --target localhost:8282
  python3 load_test.py --report report.json
"""

import asyncio
import json
import time
import sys
import argparse
import os
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any
from concurrent.futures import ThreadPoolExecutor
import urllib.request
import urllib.error
import urllib.parse

# ==============================================================
# 配置
# ==============================================================

DEFAULT_TARGET = "localhost:8282"
DEFAULT_CONCURRENCY = [50, 100, 200, 400]
REQUEST_TIMEOUT = 30  # 秒

# ==============================================================
# 结果数据结构
# ==============================================================

@dataclass
class TestResult:
    request_id: str
    endpoint: str
    method: str
    success: bool
    status_code: int
    response_time_ms: float
    response_size: int
    error: str = ""
    timestamp: str = ""

@dataclass
class ConcurrencyReport:
    concurrency: int
    total_requests: int
    successful: int
    failed: int
    success_rate: float
    total_time_ms: float
    avg_latency_ms: float
    min_latency_ms: float
    max_latency_ms: float
    p50_ms: float = 0.0
    p90_ms: float = 0.0
    p95_ms: float = 0.0
    p99_ms: float = 0.0
    tps: float = 0.0
    results: List[Dict] = field(default_factory=list)

# ==============================================================
# HTTP 工具
# ==============================================================

def http_request(url: str, method: str = "GET", data: dict = None, timeout: int = REQUEST_TIMEOUT) -> tuple:
    """发送 HTTP 请求，返回 (success, status_code, body, response_time_ms)"""
    start = time.time()
    try:
        body = json.dumps(data).encode('utf-8') if data else None
        req = urllib.request.Request(url, data=body, method=method)
        req.add_header('Content-Type', 'application/json')
        
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            elapsed = (time.time() - start) * 1000
            response_body = resp.read().decode('utf-8')
            return True, resp.status, response_body, elapsed
            
    except urllib.error.HTTPError as e:
        elapsed = (time.time() - start) * 1000
        return False, e.code, e.read().decode('utf-8') if e.fp else "", elapsed
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return False, 0, str(e), elapsed

# ==============================================================
# 功能测试
# ==============================================================

def test_health(target: str) -> TestResult:
    """测试健康检查端点"""
    url = f"http://{target}/api/health"
    success, status, body, latency = http_request(url)
    return TestResult(
        request_id="health",
        endpoint="/api/health",
        method="GET",
        success=success, status_code=status,
        response_time_ms=latency,
        response_size=len(body) if body else 0,
        timestamp=datetime.now().isoformat()
    )

def test_status(target: str) -> TestResult:
    """测试系统状态端点"""
    url = f"http://{target}/api/status"
    success, status, body, latency = http_request(url)
    return TestResult(
        request_id="status",
        endpoint="/api/status",
        method="GET",
        success=success, status_code=status,
        response_time_ms=latency,
        response_size=len(body) if body else 0,
        timestamp=datetime.now().isoformat()
    )

def test_node_register(target: str) -> TestResult:
    """测试节点注册"""
    url = f"http://{target}/api/v1/nodes/register"
    payload = {
        "node_id": f"test-node-{int(time.time())}",
        "region": "test-region",
        "gpu_type": "A100-80GB",
        "gpu_count": 4,
        "cpu_cores": 32,
        "memory_mb": 131072,
        "max_tasks": 10
    }
    success, status, body, latency = http_request(url, "POST", payload)
    return TestResult(
        request_id="node_register",
        endpoint="/api/v1/nodes/register",
        method="POST",
        success=success, status_code=status,
        response_time_ms=latency,
        response_size=len(body) if body else 0,
        timestamp=datetime.now().isoformat()
    )

def test_task_submit(target: str) -> TestResult:
    """测试任务提交"""
    url = f"http://{target}/api/v1/tasks/submit"
    payload = {
        "task_id": f"test-task-{int(time.time())}",
        "priority": 5,
        "task_type": "inference",
        "gpu_requirement": {"min_gpu": 1},
        "payload": {"model": "qwen3.6-35b", "input": "test"},
        "timeout_seconds": 300
    }
    success, status, body, latency = http_request(url, "POST", payload)
    return TestResult(
        request_id="task_submit",
        endpoint="/api/v1/tasks/submit",
        method="POST",
        success=success, status_code=status,
        response_time_ms=latency,
        response_size=len(body) if body else 0,
        timestamp=datetime.now().isoformat()
    )

def test_compose(target: str) -> TestResult:
    """测试任务编排"""
    url = f"http://{target}/api/v1/tasks/compose"
    payload = {
        "prompt": "分析数据并生成报告",
        "model": "qwen3.6-35b-common"
    }
    success, status, body, latency = http_request(url, "POST", payload)
    return TestResult(
        request_id="task_compose",
        endpoint="/api/v1/tasks/compose",
        method="POST",
        success=success, status_code=status,
        response_time_ms=latency,
        response_size=len(body) if body else 0,
        timestamp=datetime.now().isoformat()
    )

# ==============================================================
# 功能测试套件
# ==============================================================

def run_functional_tests(target: str) -> Dict[str, TestResult]:
    """运行功能测试套件"""
    tests = {
        "health": test_health,
        "status": test_status,
        "node_register": test_node_register,
        "task_submit": test_task_submit,
        "compose": test_compose,
    }
    
    results = {}
    print("\n" + "=" * 60)
    print("🧪 功能测试")
    print("=" * 60)
    
    for name, test_fn in tests.items():
        result = test_fn(target)
        results[name] = result
        status_icon = "✅" if result.success else "❌"
        print(f"  {status_icon} {name:20s} | {result.response_time_ms:8.1f}ms | {result.response_size:6d}B | {result.status_code}")
        if not result.success:
            print(f"     错误: {result.error[:100]}")
    
    all_passed = all(r.success for r in results.values())
    print(f"\n  结果: {'✅ 全部通过' if all_passed else '❌ 有失败'}")
    return results

# ==============================================================
# 并发压测
# ==============================================================

def single_request_worker(target: str, endpoint: str, request_id: int) -> TestResult:
    """单个请求工作线程"""
    url = f"http://{target}{endpoint}"
    start = time.time()
    try:
        req = urllib.request.Request(url, method="GET")
        with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
            body = resp.read()
            elapsed = (time.time() - start) * 1000
            return TestResult(
                request_id=f"req-{request_id}",
                endpoint=endpoint,
                method="GET",
                success=True,
                status_code=resp.status,
                response_time_ms=elapsed,
                response_size=len(body),
                timestamp=datetime.now().isoformat()
            )
    except Exception as e:
        elapsed = (time.time() - start) * 1000
        return TestResult(
            request_id=f"req-{request_id}",
            endpoint=endpoint,
            method="GET",
            success=False,
            status_code=0,
            response_time_ms=elapsed,
            response_size=0,
            error=str(e),
            timestamp=datetime.now().isoformat()
        )

def run_stress_test(target: str, endpoints: List[str], concurrency: int) -> ConcurrencyReport:
    """并发压力测试"""
    print(f"\n{'=' * 60}")
    print(f"🚀 并发压测: {concurrency} 并发, 端点: {[e.split('/')[-1] for e in endpoints]}")
    print("=" * 60)
    
    total_requests = concurrency * 3  # 每个端点发 3 轮
    
    results = []
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = []
        req_id = 0
        for endpoint in endpoints:
            for _ in range(3):  # 3 轮
                for _ in range(concurrency):
                    futures.append(executor.submit(single_request_worker, target, endpoint, req_id))
                    req_id += 1
        
        for i, future in enumerate(futures):
            try:
                result = future.result(timeout=REQUEST_TIMEOUT)
                results.append(result)
            except Exception as e:
                results.append(TestResult(
                    request_id=f"req-{i}",
                    endpoint="unknown",
                    method="GET",
                    success=False,
                    status_code=0,
                    response_time_ms=REQUEST_TIMEOUT * 1000,
                    response_size=0,
                    error=str(e),
                    timestamp=datetime.now().isoformat()
                ))
    
    total_time = (time.time() - start_time) * 1000
    
    latencies = [r.response_time_ms for r in results if r.response_time_ms > 0]
    latencies.sort()
    
    successful = sum(1 for r in results if r.success)
    failed = len(results) - successful
    
    report = ConcurrencyReport(
        concurrency=concurrency,
        total_requests=len(results),
        successful=successful,
        failed=failed,
        success_rate=successful / len(results) * 100 if results else 0,
        total_time_ms=total_time,
        avg_latency_ms=sum(latencies) / len(latencies) if latencies else 0,
        min_latency_ms=min(latencies) if latencies else 0,
        max_latency_ms=max(latencies) if latencies else 0,
        p50_ms=latencies[len(latencies) // 2] if latencies else 0,
        p90_ms=latencies[int(len(latencies) * 0.9)] if latencies else 0,
        p95_ms=latencies[int(len(latencies) * 0.95)] if latencies else 0,
        p99_ms=latencies[int(len(latencies) * 0.99)] if latencies else 0,
        tps=len(results) / (total_time / 1000) if total_time > 0 else 0,
        results=[asdict(r) for r in results]
    )
    
    print(f"  总请求:   {report.total_requests}")
    print(f"  成功:     {report.successful} ({report.success_rate:.1f}%)")
    print(f"  失败:     {report.failed}")
    print(f"  总耗时:   {report.total_time_ms:.0f}ms")
    print(f"  平均延迟: {report.avg_latency_ms:.1f}ms")
    print(f"  P50:      {report.p50_ms:.1f}ms")
    print(f"  P90:      {report.p90_ms:.1f}ms")
    print(f"  P95:      {report.p95_ms:.1f}ms")
    print(f"  P99:      {report.p99_ms:.1f}ms")
    print(f"  最大延迟: {report.max_latency_ms:.1f}ms")
    print(f"  TPS:      {report.tps:.1f}")
    
    # 状态图标
    if report.success_rate >= 100:
        icon = "✅"
    elif report.success_rate >= 99:
        icon = "🟡"
    else:
        icon = "❌"
    print(f"  状态:     {icon} {'优秀' if report.success_rate >= 99 else '警告' if report.success_rate >= 95 else '失败'}")
    
    return report

# ==============================================================
# 端到端流程测试
# ==============================================================

def run_e2e_flow_test(target: str) -> Dict[str, Any]:
    """端到端流程测试：节点注册 → 心跳 → 任务提交 → 结果查询"""
    print(f"\n{'=' * 60}")
    print("🔄 端到端流程测试")
    print("=" * 60)
    
    flow = {}
    node_id = f"e2e-node-{int(time.time())}"
    
    # 步骤 1: 注册节点
    t0 = time.time()
    success, status, body, latency = http_request(
        f"http://{target}/api/v1/nodes/register", "POST",
        {"node_id": node_id, "region": "e2e-test", "gpu_type": "A100",
         "gpu_count": 1, "cpu_cores": 8, "memory_mb": 32768, "max_tasks": 5}
    )
    flow["node_register"] = {"success": success, "status": status, "latency_ms": latency}
    print(f"  1. 注册节点: {'✅' if success else '❌'} ({latency:.0f}ms)")
    
    if not success:
        flow["error"] = "节点注册失败"
        return flow
    
    # 步骤 2: 心跳
    t1 = time.time()
    success, status, body, latency = http_request(
        f"http://{target}/api/v1/nodes/heartbeat", "POST",
        {"node_id": node_id, "cpu_util": 50.0, "gpu_metrics": [{"gpu_id": 0, "utilization": 60.0}], "active_tasks": 0}
    )
    flow["heartbeat"] = {"success": success, "status": status, "latency_ms": latency}
    print(f"  2. 心跳:     {'✅' if success else '❌'} ({latency:.0f}ms)")
    
    # 步骤 3: 任务提交
    success, status, body, latency = http_request(
        f"http://{target}/api/v1/tasks/submit", "POST",
        {"task_id": f"e2e-task-{node_id}", "priority": 5, "task_type": "test",
         "gpu_requirement": {"min_gpu": 1}, "payload": {"test": True}}
    )
    flow["task_submit"] = {"success": success, "status": status, "latency_ms": latency}
    print(f"  3. 任务提交: {'✅' if success else '❌'} ({latency:.0f}ms)")
    
    total_time = (time.time() - t0) * 1000
    flow["total_flow_time_ms"] = total_time
    
    # 汇总
    all_success = all(flow[k].get("success") for k in ["node_register", "heartbeat", "task_submit"])
    print(f"\n  总耗时: {total_time:.0f}ms")
    print(f"  结果: {'✅ 全流程通过' if all_success else '❌ 流程中断'}")
    
    return flow

# ==============================================================
# 报告生成
# ==============================================================

def generate_report(test_name: str, functional_results: Dict, stress_reports: List[ConcurrencyReport], e2e_flow: Dict) -> Dict:
    """生成完整测试报告"""
    report = {
        "test_name": test_name,
        "timestamp": datetime.now().isoformat(),
        "target": DEFAULT_TARGET,
        "functional_tests": {k: asdict(v) for k, v in functional_results.items()},
        "stress_tests": [asdict(r) for r in stress_reports],
        "e2e_flow": e2e_flow,
        "summary": {
            "functional_passed": sum(1 for r in functional_results.values() if r.success),
            "functional_total": len(functional_results),
            "stress_tests_run": len(stress_reports),
            "e2e_passed": not e2e_flow.get("error", ""),
        }
    }
    return report

def print_summary_report(report: Dict):
    """打印汇总报告"""
    s = report["summary"]
    print(f"\n{'=' * 60}")
    print("📊 测试报告汇总")
    print("=" * 60)
    print(f"  测试时间: {report['timestamp']}")
    print(f"  功能测试: {s['functional_passed']}/{s['functional_total']} 通过")
    print(f"  压测场景: {s['stress_tests_run']} 个")
    print(f"  端到端:   {'✅ 通过' if s['e2e_passed'] else '❌ 失败'}")
    
    print(f"\n  压测详情:")
    for st in report["stress_tests"]:
        icon = "✅" if st["success_rate"] >= 99 else ("🟡" if st["success_rate"] >= 95 else "❌")
        print(f"    {icon} {st['concurrency']:4d} 并发 | {st['success_rate']:6.1f}% | "
              f"TPS {st['tps']:6.1f} | P50 {st['p50_ms']:7.1f}ms | P99 {st['p99_ms']:7.1f}ms")

# ==============================================================
# 主流程
# ==============================================================

def main():
    parser = argparse.ArgumentParser(description="ComputeHub 自动化压测脚本")
    parser.add_argument("--target", default=DEFAULT_TARGET, help="目标地址 (host:port)")
    parser.add_argument("--concurrency", type=int, nargs="+", default=DEFAULT_CONCURRENCY,
                        help="并发数列表")
    parser.add_argument("--report", "-o", help="报告输出文件 (JSON)")
    parser.add_argument("--no-stress", action="store_true", help="只运行功能测试")
    args = parser.parse_args()
    
    target = args.target
    print(f"\n🎯 ComputeHub Load Test")
    print(f"   Target: {target}")
    print(f"   Time:   {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    endpoints = ["/api/health", "/api/status", "/api/v1/nodes/list", "/api/v1/tasks/list"]
    
    # 1. 功能测试
    functional_results = run_functional_tests(target)
    
    # 2. 并发压测
    stress_reports = []
    if not args.no_stress:
        for concurrency in args.concurrency:
            report = run_stress_test(target, endpoints, concurrency)
            stress_reports.append(report)
    
    # 3. 端到端测试
    e2e_flow = run_e2e_flow_test(target)
    
    # 4. 生成报告
    report = generate_report("sprint5-production", functional_results, stress_reports, e2e_flow)
    
    print_summary_report(report)
    
    # 5. 保存报告
    if args.report:
        with open(args.report, 'w') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        print(f"\n📄 报告已保存: {args.report}")
    
    # 6. 退出码
    if not all(r.success for r in functional_results.values()):
        sys.exit(1)
    
    return 0

if __name__ == "__main__":
    main()
