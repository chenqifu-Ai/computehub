#!/usr/bin/env python3
"""
ComputeHub Worker 自更新任务
=============================
向 cqf-worker-02 提交任务，让其自我更新二进制文件。

关键设计：Worker 不能在自己执行的任务里杀掉自己。
方案：先启动新 Worker，再安排一个延迟清理脚本（等任务退出后执行）。

流程：
  1. 下载新二进制 → D:\computehub-worker-new.exe
  2. 用 START 启动新 Worker（彻底脱离父进程）
  3. 创建 cleanup.cmd 延迟 15 秒后杀掉旧进程 + 文件重命名
  4. 用 START 启动 cleanup.cmd（后台执行）
  5. 任务正常退出
  6. 15 秒后 cleanup.cmd 执行清理
"""

import requests
import json
import time
import sys

GATEWAY = "http://192.168.1.7:8282"
NODE_ID = "cqf-worker-02"
OLD_PID = 12372  # 当前 worker 进程 PID

def submit_task(task_id: str, command: str, timeout: int = 60):
    """提交任务到 worker"""
    r = requests.post(f"{GATEWAY}/api/v1/tasks/submit", json={
        "task_id": task_id,
        "node_id": NODE_ID,
        "command": command,
        "timeout_seconds": timeout,
        "priority": 8
    }, timeout=10)
    return r.json()

def wait_for_result(task_id: str, max_wait: int = 120, interval: int = 3):
    """轮询等待任务结果"""
    for i in range(max_wait // interval):
        time.sleep(interval)
        r = requests.get(f"{GATEWAY}/api/v1/tasks/detail", params={
            "task_id": task_id,
            "node_id": NODE_ID
        }, timeout=10)
        d = r.json()
        if not d.get("success"):
            continue
        data = d.get("data", {})
        status = data.get("status")
        if status == "completed":
            return data
        if status == "failed" or status == "error":
            return data
    return None

def check_worker_count(interval: int = 3):
    """查看当前在线节点数"""
    r = requests.get(f"{GATEWAY}/api/v1/nodes/list", timeout=10)
    d = r.json()
    if d.get("success"):
        return len(d.get("data", []))
    return 0

def main():
    print("=" * 55)
    print("  🚀 ComputeHub Worker 自更新任务")
    print(f"  📡 网关: {GATEWAY}")
    print(f"  🖥️  目标: {NODE_ID} (PID {OLD_PID})")
    print(f"  🕐 {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 55)
    print()

    # ── 当前节点数（对比用） ──
    before_count = check_worker_count()
    print(f"  [状态] 当前在线节点数: {before_count}")
    print()

    # ── Step 1: 构建命令 ──
    print("[1/4] 构建自更新命令...")

    # Windows CMD 命令（Worker 通过 cmd /c 执行）
    # 关键：用 START 启动后台进程，脱离父进程
    cmd = (
        # 1. 下载新二进制
        f'echo === [1/4] 下载新二进制 ==='
        f' && curl -s -o D:\\computehub-worker-new.exe '
        f'"{GATEWAY}/api/v1/download?file=compute-worker-win-amd64.exe"'
        f' && echo   完成: & for %%A in (D:\\computehub-worker-new.exe) do echo %%~zA bytes'
        
        # 2. 验证文件
        f' && echo === [2/4] 验证文件 ==='
        f' && if not exist D:\\computehub-worker-new.exe (echo ❌ 下载失败 & exit /b 1)'
        
        # 3. 启动新 Worker（彻底后台，不等待）
        #    START /B = 当前窗口后台 ; START "" = 新窗口
        #    用 /MIN 最小化窗口运行，避免弹黑框
        f' && echo === [3/4] 启动新 Worker ==='
        f' && START /MIN "" D:\\computehub-worker-new.exe '
        f'--gw {GATEWAY} '
        f'--node-id {NODE_ID} '
        f'--region cn-east '
        f'--interval 0.5 '
        f'--heartbeat 10 '
        f'--concurrent 6'
        f' && echo   新进程已启动（后台运行）'
        
        # 4. 创建清理脚本（延迟执行，这样任务可以正常退出）
        #    cleanup.cmd 会在 15 秒后杀掉旧 PID + 重命名文件
        f' && echo === [4/4] 安排延时清理 ==='
        f' && echo @echo off > D:\\cleanup_worker.cmd'
        f' && echo echo === Worker 清理脚本 === >> D:\\cleanup_worker.cmd'
        f' && echo ping -n 16 127.0.0.1 ^>nul >> D:\\cleanup_worker.cmd'
        f' && echo echo [1/3] 杀掉旧进程 PID {OLD_PID}... >> D:\\cleanup_worker.cmd'
        f' && echo taskkill /F /PID {OLD_PID} 2^>nul >> D:\\cleanup_worker.cmd'
        f' && echo if exist D:\\computehub-worker.exe ( >> D:\\cleanup_worker.cmd'
        f' && echo   move /Y D:\\computehub-worker.exe D:\\computehub-worker-backup.exe ^>nul >> D:\\cleanup_worker.cmd'
        f' && echo   echo [2/3] 旧二进制已备份 >> D:\\cleanup_worker.cmd'
        f' && echo ) >> D:\\cleanup_worker.cmd'
        f' && echo move /Y D:\\computehub-worker-new.exe D:\\computehub-worker.exe ^>nul >> D:\\cleanup_worker.cmd'
        f' && echo echo [3/3] 新二进制已就位 >> D:\\cleanup_worker.cmd'
        f' && echo echo === ✅ 清理完成 === >> D:\\cleanup_worker.cmd'
        
        # 5. 启动清理脚本（后台，不阻塞）
        f' && START /MIN "" D:\\cleanup_worker.cmd'
        f' && echo   清理脚本已在后台安排（15 秒后执行）'
        
        # 6. 确认新进程启动
        f' && echo === ✅ 自更新流程已触发 ==='
        f' && echo   任务正常退出，清理脚本将在后台完成剩余工作'
    )

    task_id = f"selfupdate-{int(time.time())}"
    # 用 cmd /c 执行，Worker 本身通过 cmd 运行
    full_cmd = f"cmd /c {cmd}"

    print(f"  命令长度: {len(full_cmd)} 字符")
    print(f"  任务 ID: {task_id}")
    print()

    # ── Step 2: 提交任务 ──
    print("[2/4] 提交任务...")
    resp = submit_task(task_id, full_cmd, timeout=60)
    print(f"  提交结果: {resp}")
    print()

    if not resp.get("success"):
        print("❌ 任务提交失败，退出")
        sys.exit(1)

    # ── Step 3: 等待执行结果 ──
    print("[3/4] 等待任务执行 (最长 120 秒)...")
    result = wait_for_result(task_id, max_wait=120, interval=5)

    if result:
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        exit_code = result.get("exit_code")
        duration = result.get("duration")
        print(f"  ✅ 任务完成 (exit_code={exit_code}, duration={duration})")
        print()
        if stdout:
            print("  === STDOUT ===")
            for line in stdout.split("\n"):
                if line.strip():
                    print(f"  {line.strip()}")
        if stderr:
            stderr_clean = stderr.replace("\ufffd", "?").replace("\u0373", "?").replace("\u03e5", "?")
            print("  === STDERR ===")
            for line in stderr_clean.split("\n"):
                if line.strip():
                    print(f"  {line.strip()}")
    else:
        print("  ⏳ 任务未在规定时间内完成")
        # 可能清理脚本先杀了 Worker，正常

    # ── Step 4: 等待清理完成 + 验证新的 Worker 上线 ──
    print()
    print("[4/4] 等待清理脚本执行 + 新 Worker 上线...")
    print("  等待 20 秒...")
    time.sleep(20)

    # 检查节点列表
    r = requests.get(f"{GATEWAY}/api/v1/nodes/list", timeout=10)
    if r.json().get("success"):
        nodes = r.json().get("data", [])
        print(f"\n  当前在线节点数: {len(nodes)}")
        for n in nodes:
            print(f"    {n['node_id']:20s} | {n['status']:8s} | GPU={n['gpu_type']:8s} | 活跃={n['active_tasks']}")

        if len(nodes) >= before_count:
            print(f"\n  ✅ 自更新成功！Worker 已重新上线")
        else:
            print(f"\n  ⚠️  节点数未恢复，可能需要检查")

    # ── 最终状态 ──
    print()
    print("=" * 55)
    print("  📊 最终状态")
    print()
    r = requests.get(f"{GATEWAY}/api/v1/tasks/list", timeout=10)
    if r.json().get("success"):
        all_tasks = r.json().get("data", {})
        total = sum(len(ts) for ts in all_tasks.values())
        print(f"  总任务数: {total}")
    print("=" * 55)


if __name__ == "__main__":
    main()
