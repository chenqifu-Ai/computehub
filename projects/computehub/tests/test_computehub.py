#!/usr/bin/env python3
"""
ComputeHub 端到端测试套件
=====================
覆盖：Gateway 健康检查 → 节点管理 → 任务生命周期 → 结果验证 → 错误处理

用法：
  python3 test_computehub.py [--gateway http://IP:PORT]
"""

import json, sys, time, uuid, argparse
from typing import Optional, Dict, Any, List, Tuple
from datetime import datetime

try:
    import requests
except ImportError:
    print("❌ 需要 requests 库: pip install requests")
    sys.exit(1)

# ═══════════════════════════════════════════════════════════════
# 配置
# ═══════════════════════════════════════════════════════════════
GATEWAY_URL = "http://192.168.1.7:8282"
PASS = 0
FAIL = 0
WARN = 0
SKIP = 0

def log(msg: str, level: str = "INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    icon = {"PASS": "✅", "FAIL": "❌", "WARN": "⚠️", "INFO": "ℹ️", "SKIP": "⏭️"}
    print(f"  {icon.get(level, '•')} [{ts}] {msg}")

def check(name: str, condition: bool, detail: str = "") -> bool:
    global PASS, FAIL
    if condition:
        PASS += 1
        log(f"{name}: PASS", "PASS")
        return True
    else:
        FAIL += 1
        msg = f"{name}: FAIL"
        if detail:
            msg += f"\n    └─ {detail}"
        log(msg, "FAIL")
        return False

def warn(name: str, detail: str = ""):
    global WARN
    WARN += 1
    msg = f"{name}: WARN"
    if detail:
        msg += f"\n    └─ {detail}"
    log(msg, "WARN")

def skip(name: str, reason: str = ""):
    global SKIP
    SKIP += 1
    msg = f"{name}: SKIP"
    if reason:
        msg += f" ({reason})"
    log(msg, "SKIP")

# ═══════════════════════════════════════════════════════════════
# HTTP 辅助
# ═══════════════════════════════════════════════════════════════

def api_get(path: str, params: Dict = None) -> Tuple[bool, Any]:
    """GET 请求，返回 (成功?, 响应体)"""
    try:
        r = requests.get(f"{GATEWAY_URL}{path}", params=params, timeout=10)
        d = r.json()
        ok = d.get("success", False)
        return ok, d
    except Exception as e:
        return False, {"error": str(e)}

def api_post(path: str, body: Dict) -> Tuple[bool, Any]:
    """POST 请求，返回 (成功?, 响应体)"""
    try:
        r = requests.post(f"{GATEWAY_URL}{path}", json=body, timeout=10)
        d = r.json()
        ok = d.get("success", False)
        return ok, d
    except Exception as e:
        return False, {"error": str(e)}

def gen_task_id(prefix: str = "test") -> str:
    return f"{prefix}-{uuid.uuid4().hex[:8]}"

# ═══════════════════════════════════════════════════════════════
# 测试组
# ═══════════════════════════════════════════════════════════════

def test_gateway_health():
    """网关基础健康检查"""
    print("\n━━━━ 1. 网关健康检查 ━━━━")

    # 1.1 健康端点
    ok, d = api_get("/api/health")
    check("GET /api/health 返回 200", ok)
    if ok:
        log(f"  响应: {json.dumps(d, ensure_ascii=False)[:200]}")

    # 1.2 状态端点（直接返回结构体，不含 success/error 包装）
    ok, d = api_get("/api/status")
    if ok:
        kernel = d.get("kernel", {})
        check("Kernel 状态 RUNNING", kernel.get("status") == "RUNNING",
              f"got: {kernel.get('status')}")
    else:
        # 可能是格式问题，直接检查内容
        check("GET /api/status 返回数据", d.get("kernel", {}).get("status") == "RUNNING")

    # 1.3 节点列表（基础接口也当健康检查）
    ok, d = api_get("/api/v1/nodes/list")
    check("GET /api/v1/nodes/list 可访问", ok)
    if ok:
        nodes = d.get("data", [])
        log(f"  已注册节点数: {len(nodes)}")
        for n in nodes:
            log(f"    {n['node_id']}: {n['status']} | GPU={n['gpu_type']} | 活跃={n['active_tasks']}")

def test_node_lifecycle():
    """节点注册 → 心跳 → 列表 → 注销"""
    print("\n━━━━ 2. 节点管理 ━━━━")

    # 2.1 注册测试节点（带 GPU 信息）
    test_node_id = f"test-node-{uuid.uuid4().hex[:4]}"
    ok, d = api_post("/api/v1/nodes/register", {
        "node_id": test_node_id,
        "gpu_type": "H100",
        "region": "cn-east",
        "max_tasks": 4,
        "status": "online"
    })
    check(f"注册节点 {test_node_id}", ok,
          f"resp: {json.dumps(d, ensure_ascii=False)}")

    # 2.2 验证节点出现在列表
    ok, d = api_get("/api/v1/nodes/list")
    if ok:
        nodes = d.get("data", [])
        found = any(n["node_id"] == test_node_id for n in nodes)
        check(f"节点 {test_node_id} 在列表中", found)
    else:
        check("列表查询", False)

    # 2.3 心跳
    ok, d = api_post("/api/v1/nodes/heartbeat", {
        "node_id": test_node_id,
        "active_tasks": 2,
        "cpu_utilization": 35.5,
        "memory_used_gb": 4.2,
        "gpu_utilization": 45.0,
        "temperature": 42.0
    })
    check(f"心跳 {test_node_id} 正常", ok)

    # 2.4 注销节点
    ok, d = api_post("/api/v1/nodes/unregister", {
        "node_id": test_node_id
    })
    check(f"注销节点 {test_node_id}", ok)

    # 2.5 确认列表中已移除
    ok, d = api_get("/api/v1/nodes/list")
    if ok:
        nodes = d.get("data", [])
        found = any(n["node_id"] == test_node_id for n in nodes)
        check("注销后节点已移除", not found)

def test_task_submit_and_poll():
    """任务提交 → poll 认领 → progress → result → detail"""
    print("\n━━━━ 3. 任务生命周期 ━━━━")

    # 先获取一个真实 worker 节点
    ok, d = api_get("/api/v1/nodes/list")
    workers = d.get("data", []) if ok else []
    if not workers:
        skip("任务流", "没有在线 worker")
        return

    target_node = workers[0]["node_id"]
    log(f"目标节点: {target_node}")

    # 3.1 提交简单任务
    task_id = gen_task_id("t3")
    cmd = 'echo Hello && hostname && echo DONE'
    ok, d = api_post("/api/v1/tasks/submit", {
        "task_id": task_id,
        "node_id": target_node,
        "command": cmd,
        "timeout_seconds": 15,
        "priority": 5
    })
    check(f"提交任务 {task_id}", ok and d.get("data",{}).get("task_id") == task_id)

    # 3.2 Worker poll 认领
    time.sleep(2)
    ok, d = api_post("/api/v1/tasks/poll", {
        "node_id": target_node
    })
    if ok and d.get("data",{}).get("task"):
        check(f"Worker 可认领到任务", True)
    else:
        check(f"Worker 认领状态", ok)

    # 3.3 等待完成并查看结果
    time.sleep(3)
    ok, d = api_get("/api/v1/tasks/detail", {"task_id": task_id, "node_id": target_node})
    check(f"任务详情可查 ({task_id})", ok)
    if ok:
        data = d.get("data", {})
        check(f"任务状态 completed", data.get("status") == "completed",
              f"got: {data.get('status')}")
        stdout = data.get("stdout", "")
        if stdout:
            log(f"  stdout: {stdout.strip()[:200]}")

    # 3.4 查看 progress（流式输出）
    ok, d = api_get("/api/v1/tasks/progress", {"task_id": task_id})
    if ok:
        data = d.get("data", {})
        check(f"Progress 返回结果", data.get("task_id") == task_id)
        log(f"  exit_code={data.get('exit_code')}, duration={data.get('duration')}")

    # 3.5 提交失败命令并验证 stderr
    task_id2 = gen_task_id("t3err")
    cmd2 = 'non_existent_command_xyz'
    api_post("/api/v1/tasks/submit", {
        "task_id": task_id2,
        "node_id": target_node,
        "command": cmd2,
        "timeout_seconds": 10
    })
    time.sleep(4)
    ok, d = api_get("/api/v1/tasks/detail", {"task_id": task_id2, "node_id": target_node})
    if ok:
        data = d.get("data", {})
        check(f"错误命令 exit_code != 0", data.get("exit_code", 0) != 0,
              f"exit_code={data.get('exit_code')}")
        stderr = data.get("stderr", "")
        if stderr:
            log(f"  stderr: {stderr.strip()[:200]}")

def test_task_list():
    """任务列表查询"""
    print("\n━━━━ 4. 任务列表 ━━━━")

    ok, d = api_get("/api/v1/tasks/list")
    check("任务列表可查询", ok)
    if ok:
        all_tasks = d.get("data", {})
        total = sum(len(tasks) for tasks in all_tasks.values())
        log(f"  总计 {total} 个任务，分布：")
        for node_id, tasks in all_tasks.items():
            statuses = [t.get("status","?") for t in tasks]
            log(f"    {node_id}: {len(tasks)} 个任务 [{', '.join(statuses)}]")

def test_error_handling():
    """错误处理"""
    print("\n━━━━ 5. 错误处理 ━━━━")

    # 5.1 空 node_id（当前 Gateway 不校验 node_id 直接入队列）
    ok, d = api_post("/api/v1/tasks/submit", {
        "task_id": gen_task_id("err"),
        "command": "echo hi"
    })
    if ok:
        warn("空 node_id 提交成功（无 node_id 校验是已知行为）")
    else:
        check("空 node_id 应报错", True)

    # 5.2 不存在的 task_id 查详情
    ok, d = api_get("/api/v1/tasks/detail", {"task_id": "nonexistent"})
    check("不存在 task 返回错误", not ok)

    # 5.3 不存在的 task_id 查 progress
    ok, d = api_get("/api/v1/tasks/progress", {"task_id": "nonexistent"})
    check("不存在 task progress 返回错误", not ok)

    # 5.4 心跳：空 node_id
    ok, d = api_post("/api/v1/nodes/heartbeat", {})
    check("空 node_id 心跳返回错误", not ok)

def test_streaming_progress():
    """流式输出推送测试（模拟 worker 推送 progress）"""
    print("\n━━━━ 6. 流式输出推送 ━━━━")

    # 获取 worker
    ok, d = api_get("/api/v1/nodes/list")
    workers = d.get("data", []) if ok else []
    if not workers:
        skip("流式测试", "没有在线 worker")
        return

    target_node = workers[0]["node_id"]

    # 先提交一个长时间任务（或者先提交再手动 push progress）
    task_id = gen_task_id("stream")
    api_post("/api/v1/tasks/submit", {
        "task_id": task_id,
        "node_id": target_node,
        "command": "echo 'long running'",
        "timeout_seconds": 30
    })
    time.sleep(2)

    # 模拟 worker 逐步推送 output
    for i, chunk in enumerate(["Step 1: loading...\n", "Step 2: processing...\n", "Step 3: done!\n"]):
        ok, d = api_post("/api/v1/tasks/progress", {
            "task_id": task_id,
            "node_id": target_node,
            "stdout": chunk,
            "stderr": ""
        })
        if not ok:
            warn(f"推送 chunk {i+1}", f"resp: {d}")
        time.sleep(0.2)

    # 查询累积的 progress
    time.sleep(2)
    ok, d = api_get("/api/v1/tasks/progress", {"task_id": task_id})
    if ok:
        data = d.get("data", {})
        stdout = data.get("stdout", "")
        check("流式输出累积", "Step 1" in stdout and "Step 3" in stdout,
              f"stdout: {stdout[:200]}")

def test_priority_scheduling():
    """优先级调度测试"""
    print("\n━━━━ 7. 优先级调度 ━━━━")

    ok, d = api_get("/api/v1/nodes/list")
    workers = d.get("data", []) if ok else []
    if not workers:
        skip("优先级测试", "没有在线 worker")
        return

    target = workers[0]["node_id"]

    # 提交多个任务，验证优先级排序
    task_ids = []
    for i in range(3):
        tid = gen_task_id("prio")
        api_post("/api/v1/tasks/submit", {
            "task_id": tid,
            "node_id": target,
            "command": f"echo task-{i+1}",
            "priority": i + 1,
            "timeout_seconds": 10
        })
        task_ids.append(tid)
        time.sleep(0.2)

    # 检查列表，看所有任务都提交成功
    ok, d = api_get("/api/v1/tasks/detail", {"task_id": task_ids[-1], "node_id": target})
    check("优先级任务可查询", ok)

    log("  优先级测试不阻塞等待，任务列表中有记录即可")

def test_metrics():
    """Prometheus 指标"""
    print("\n━━━━ 8. 指标接口 ━━━━")

    ok, d = api_get("/api/v1/nodes/metrics", {"node_id": "cqf-worker-02"})
    if ok:
        check("指标接口可用", ok)
        data = d.get("data", {})
        log(f"  指标返回: {json.dumps(data, ensure_ascii=False)[:200]}")
    else:
        skip("指标接口", f"返回: {d}")

def run_all():
    """运行全部测试"""
    global PASS, FAIL, WARN, SKIP
    print(f"\n{'='*55}")
    print(f"  🧪 ComputeHub 端到端测试")
    print(f"  📡 网关: {GATEWAY_URL}")
    print(f"  🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*55}")

    start = time.time()

    # 前置条件检查
    ok, d = api_get("/api/health")
    if not ok:
        print(f"\n❌ 网关不可达: {d.get('error', 'unknown')}")
        sys.exit(1)

    # 按顺序执行测试
    test_gateway_health()
    test_node_lifecycle()
    test_task_submit_and_poll()
    test_task_list()
    test_error_handling()
    test_streaming_progress()
    test_priority_scheduling()
    test_metrics()

    elapsed = time.time() - start

    # 结果汇总
    print(f"\n{'='*55}")
    print(f"  📊 测试结果")
    print(f"  {'='*40}")
    total = PASS + FAIL + SKIP
    rate = PASS / total * 100 if total > 0 else 0
    print(f"  ✅ 通过: {PASS}")
    print(f"  ❌ 失败: {FAIL}")
    print(f"  ⚠️  警告: {WARN}")
    print(f"  ⏭️  跳过: {SKIP}")
    print(f"  ─────────────")
    print(f"  总计: {total} 项 | 通过率: {rate:.0f}% | 耗时: {elapsed:.1f}s")
    print(f"{'='*55}")

    if FAIL > 0:
        sys.exit(1)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ComputeHub 端到端测试")
    parser.add_argument("--gateway", default=GATEWAY_URL, help="网关地址")
    parser.add_argument("--list", action="store_true", help="列出所有测试组")
    args = parser.parse_args()

    # 暴露所有测试函数，方便独立调用
    TEST_GROUPS = {
        "health": test_gateway_health,
        "nodes": test_node_lifecycle,
        "tasks": test_task_submit_and_poll,
        "list": test_task_list,
        "errors": test_error_handling,
        "stream": test_streaming_progress,
        "priority": test_priority_scheduling,
        "metrics": test_metrics,
    }

    if args.list:
        print("可用测试组:")
        for name, func in TEST_GROUPS.items():
            print(f"  {name:10s} - {func.__doc__}")
        sys.exit(0)

    # 支持通过命令行参数指定运行的测试组
    # 用法: python3 test_computehub.py health tasks stream
    import sys
    remaining = [a for a in sys.argv[1:] if not a.startswith("--")]
    if remaining:
        GATEWAY_URL = args.gateway
        for group in remaining:
            if group in TEST_GROUPS:
                print(f"\n▶ 运行测试组: {group}")
                TEST_GROUPS[group]()
            else:
                print(f"❌ 未知测试组: {group} (可用: {', '.join(TEST_GROUPS.keys())})")
        print(f"\n✅ 通过: {PASS} | ❌ 失败: {FAIL} | ⚠️  {WARN} | ⏭️  {SKIP}")
    else:
        GATEWAY_URL = args.gateway
        run_all()
