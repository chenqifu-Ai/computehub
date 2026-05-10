#!/usr/bin/env python3
"""
ComputeHub Worker 自更新 v3
===============================
两步策略：
  1. 【下载+启动】新 Worker（当前任务）
  2. 【清理】旧进程 + 文件重命名（后续提交）

避免了「在任务中杀自己进程」的陷阱。
"""

import requests, json, time, sys

GATEWAY = "http://192.168.1.7:8282"
NODE_ID = "cqf-worker-02"
OLD_PID = 12372

def api_post(path, body, timeout=10):
    r = requests.post(f"{GATEWAY}{path}", json=body, timeout=timeout)
    return r.json()

def api_get(path, params=None, timeout=10):
    r = requests.get(f"{GATEWAY}{path}", params=params, timeout=timeout)
    return r.json()

def submit_task(task_id, command, timeout=60):
    return api_post("/api/v1/tasks/submit", {
        "task_id": task_id, "node_id": NODE_ID,
        "command": command, "timeout_seconds": timeout, "priority": 10
    })

def wait_task(task_id, max_wait=120):
    for i in range(max_wait // 5):
        time.sleep(5)
        d = api_get("/api/v1/tasks/detail", {"task_id": task_id, "node_id": NODE_ID})
        if d.get("success"):
            data = d.get("data", {})
            if data.get("status") == "completed":
                return data
    return None

def main():
    print("=" * 55)
    print("  ComputeHub Worker 自更新 v3")
    print(f"  Gateway: {GATEWAY}")
    print(f"  目标: {NODE_ID} (PID {OLD_PID})")
    print(f"  两步策略: 下载+启动 → 清理")
    print("=" * 55)

    # ── 检查初始状态 ──
    nodes_before = api_get("/api/v1/nodes/list").get("data", [])
    worker_count_before = len(nodes_before)
    print(f"\n[状态] 当前节点数: {worker_count_before}")
    for n in nodes_before:
        print(f"  {n['node_id']}: {n['status']}")
    print()

    # ── Step 1: 下载 + 启动新 Worker ──
    print("━" * 45)
    print(" STEP 1: 下载新二进制 + 启动新Worker")
    print("━" * 45)

    # 用 PowerShell 下载 + START 启动
    step1_cmd = (
        'cmd /c '
        'echo === [1/3] Download ==='
        ' && powershell -NoProfile -Command '
        '"$wc=New-Object System.Net.WebClient;'
        f' $wc.DownloadFile(\'{GATEWAY}/api/v1/download?file=compute-worker-win-amd64.exe\','
        " 'D:\\computehub-worker-new.exe');"
        ' $s=(Get-Item D:\\computehub-worker-new.exe).Length;'
        ' Write-Host (\"Download OK: $s bytes\");' 
        ' if($s -lt 1MB){exit 1}"'
        ' && echo === [2/3] Start new worker ==='
        ' && START /MIN D:\\computehub-worker-new.exe'
        f' --gw {GATEWAY} --node-id {NODE_ID} --region cn-east'
        ' --interval 0.5 --heartbeat 10 --concurrent 6'
        ' && echo === [3/3] Done ==='
        ' && echo New worker launched in background'
    )

    tid1 = "step1-" + str(int(time.time()))
    print(f"  提交任务: {tid1}")
    r = submit_task(tid1, step1_cmd, timeout=60)
    print(f"  结果: {r}")

    print("  等待任务完成...")
    result1 = wait_task(tid1, max_wait=60)

    if result1:
        print(f"\n  ✅ Step 1 完成 (exit={result1.get('exit_code')})")
        if result1.get("stdout"):
            for l in result1["stdout"].split("\n"):
                if l.strip():
                    print(f"    {l.strip()}")
        if result1.get("stderr"):
            s = result1["stderr"].replace("\ufffd","?").replace("\u0373","?").replace("\u03e5","?")
            print(f"    [stderr] {s[:200]}")
    else:
        print("  ⏳ Step 1 超时，继续执行后续步骤")

    # ── 等待新 Worker 注册 ──
    print("\n  等待新 Worker 注册 (15 秒)...")
    time.sleep(15)

    # 检查节点
    nodes_now = api_get("/api/v1/nodes/list").get("data", [])
    print(f"  当前节点数: {len(nodes_now)}")
    for n in nodes_now:
        print(f"    {n['node_id']:20s} | {n['status']}")

    new_registered = len(nodes_now) > worker_count_before
    if new_registered:
        print("  ✅ 新 Worker 已注册！")
    else:
        print("  ⚠️ 节点数未增加（可能用了同 node_id, Gateway 更新了注册信息）")

    print()

    # ── Step 2: 清理旧进程 + 文件重命名 ──
    print("━" * 45)
    print(" STEP 2: 清理旧进程 + 文件重命名")
    print("━" * 45)

    step2_cmd = (
        'cmd /c '
        'echo === Cleaning up ==='
        f' && echo Killing old PID {OLD_PID}...'
        f' && taskkill /F /PID {OLD_PID} 2>nul'
        ' && echo Old process killed'
        ' && if exist D:\\computehub-worker.exe ('
        ' move /Y D:\\computehub-worker.exe D:\\computehub-worker-backup.exe && echo Backed up old binary )'
        ' && move /Y D:\\computehub-worker-new.exe D:\\computehub-worker.exe && echo New binary renamed'
        ' && echo === Cleanup complete ==='
    )

    tid2 = "step2-" + str(int(time.time()))
    print(f"  提交任务: {tid2}")
    r = submit_task(tid2, step2_cmd, timeout=30)
    print(f"  结果: {r}")

    print("  等待清理完成...")
    result2 = wait_task(tid2, max_wait=30)

    if result2:
        print(f"\n  ✅ Step 2 完成 (exit={result2.get('exit_code')})")
        if result2.get("stdout"):
            for l in result2["stdout"].split("\n"):
                if l.strip():
                    print(f"    {l.strip()}")
    else:
        print("  ⏳ 任务未完成，继续验证")

    # ── 验证 ──
    print()
    print("━" * 45)
    print(" 最终验证")
    print("━" * 45)

    time.sleep(5)

    # 再次检查节点
    nodes_final = api_get("/api/v1/nodes/list").get("data", [])
    print(f"\n  在线节点:")
    for n in nodes_final:
        print(f"    {n['node_id']:20s} | {n['status']:8s} | GPU={n['gpu_type']}")

    # 提交一个测试任务确认新 Worker 正常工作
    print("\n  提交测试任务验证 Worker 功能...")
    tid3 = "verify-" + str(int(time.time()))
    r = submit_task(tid3, 'cmd /c echo Self-update verification OK && hostname && ver', timeout=30)
    time.sleep(5)
    r3 = api_get("/api/v1/tasks/detail", {"task_id": tid3, "node_id": NODE_ID})
    if r3.get("success") and r3["data"].get("status") == "completed":
        stdout = r3["data"].get("stdout", "")
        print(f"  ✅ 验证通过!")
        for l in stdout.split("\n"):
            if l.strip():
                print(f"    {l.strip()}")
    else:
        print(f"  ❌ 验证失败: {r3}")

    print("\n" + "=" * 55)
    print("  完成")
    print("=" * 55)

if __name__ == "__main__":
    main()
