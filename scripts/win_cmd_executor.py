#!/usr/bin/env python3
"""
win_cmd_executor.py - Windows 远程命令执行工具

使用 base64 + certutil -decode → node.exe 方式，绕过 Gateway 双引号限制。

用法:
    python3 win_cmd_executor.py --node <node-id> --script <script.js> [--timeout 30]
    python3 win_cmd_executor.py --node <node-id> --base64 <base64-string> [--timeout 30]
"""
import argparse
import base64
import json
import subprocess
import sys
import time

GATEWAY_URL = "http://36.250.122.43:8282"


def submit_task(node_id, command, timeout=30):
    """提交任务到 Gateway"""
    payload = {
        "node_id": node_id,
        "command": command,
        "timeout": timeout,
        "priority": 8
    }
    result = subprocess.run(
        ["curl", "-s", "-X", "POST", f"{GATEWAY_URL}/api/v1/tasks/submit",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload)],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    if data.get("success"):
        return data["data"]["task_id"]
    else:
        print(f"❌ 提交失败: {data.get('error', 'unknown')}")
        sys.exit(1)


def get_result(task_id):
    """获取任务结果"""
    time.sleep(15)
    result = subprocess.run(
        ["curl", "-s", f"{GATEWAY_URL}/api/v1/tasks/detail?task_id={task_id}"],
        capture_output=True, text=True
    )
    data = json.loads(result.stdout)
    dd = data.get("data", {})
    status = dd.get('status', '?')
    dur = dd.get('duration', '?')
    exit_code = dd.get('exit_code', '?')
    print(f"状态: {status} | 耗时: {dur} | 退出码: {exit_code}")
    stdout = dd.get('stdout', '')
    if stdout:
        print("=== 输出 ===")
        print(stdout)
    stderr = dd.get('stderr', '')
    if stderr and stderr.strip():
        print("=== 错误 ===")
        print(stderr.strip())
    return dd


def main():
    parser = argparse.ArgumentParser(
        description="Windows 远程命令执行工具 (base64 + certutil -decode → node.exe)"
    )
    parser.add_argument("--node", required=True, help="Windows 节点 ID (如 wanlida-opc01)")
    parser.add_argument("--script", help="本地 JS 脚本文件路径 (与 --base64 二选一)")
    parser.add_argument("--base64", help="已编码的 base64 字符串 (与 --script 二选一)")
    parser.add_argument("--timeout", type=int, default=30, help="超时秒数 (默认 30)")
    parser.add_argument("--gateway", default=GATEWAY_URL, help="Gateway URL (默认 http://36.250.122.43:8282)")

    args = parser.parse_args()

    if not args.script and not args.base64:
        parser.error("必须指定 --script 或 --base64")

    # 获取 base64
    if args.script:
        with open(args.script, 'rb') as f:
            script_bytes = f.read()
        b64 = base64.b64encode(script_bytes).decode('ascii')
    else:
        b64 = args.base64

    # 构建命令链
    cmd = (
        f'echo {b64} > C:\\temp\\script.b64 && '
        f'certutil -decode -f C:\\temp\\script.b64 C:\\temp\\script.js && '
        f'C:\\Users\\admin\\node\\node.exe C:\\temp\\script.js && '
        f'type C:\\temp\\result.txt'
    )

    print(f"📤 提交到 {args.node}...")
    print(f"   Gateway: {args.gateway}")
    task_id = submit_task(args.node, cmd, args.timeout)
    print(f"✅ 任务已提交: {task_id}")

    print("\n📥 获取结果...")
    get_result(task_id)


if __name__ == "__main__":
    main()
