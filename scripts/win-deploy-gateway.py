#!/usr/bin/env python3
"""
WIN-DEPLOY-001: Windows ComputeHub Gateway 标准化部署脚本
===========================================================
用途: 在 Windows 节点上部署/更新 ComputeHub Gateway，自动附带 config.json
用法: python3 win-deploy-gateway.py <node-id> [--port 8282] [--config path/to/config.json]

依赖: ComputeHub 集群任务 API
"""

import json, urllib.request, base64, time, sys, os, argparse

GATEWAY = "http://localhost:8282"
DEFAULT_CONFIG = {
    "composer": {
        "api_url": "https://ai.zhangtuokeji.top:9090/v1",
        "api_key": "***",
        "model": "qwen3.6-35b",
        "execute_models": ["qwen3.6-35b", "deepseek-v3.1:671b", "qwen3.6-35b-common"],
        "max_concurrency": 8,
        "timeout_seconds": 30
    },
    "agent_keys": {}
}

def submit_task(node_id, command, timeout=30):
    data = json.dumps({"node_id": node_id, "command": command, "timeout": timeout}).encode()
    req = urllib.request.Request(
        "{}/api/v1/tasks/submit".format(GATEWAY), data=data,
        headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp["data"]["task_id"]

def get_result(task_id):
    req = urllib.request.Request("{}/api/v1/tasks/detail?task_id={}".format(GATEWAY, task_id))
    resp = json.loads(urllib.request.urlopen(req).read())
    return resp["data"]

def deploy_gateway(node_id, port=8282, config_path=None):
    print("=" * 60)
    print("WIN-DEPLOY-001: Deploying Gateway to {}".format(node_id))
    print("=" * 60)

    # Step 1: Check existing Gateway
    print("\n[1/5] Checking existing Gateway...")
    task_id = submit_task(node_id, 'cmd /c "netstat -ano | findstr :{}"'.format(port), timeout=10)
    time.sleep(5)
    result = get_result(task_id)
    existing_pid = None
    for line in result.get("stdout", "").split("\n"):
        if "LISTENING" in line:
            parts = line.strip().split()
            existing_pid = parts[-1]
            print("  Found existing Gateway PID: {}".format(existing_pid))
            break
    if not existing_pid:
        print("  No existing Gateway on port {}".format(port))

    # Step 2: Check binary
    print("\n[2/5] Checking binary...")
    task_id = submit_task(node_id, 'cmd /c "dir /b C:\\temp\\computehub*.exe 2>nul"', timeout=10)
    time.sleep(3)
    result = get_result(task_id)
    binaries = [l.strip() for l in result.get("stdout", "").split("\n") if l.strip()]
    print("  Found binaries: {}".format(binaries))

    # Step 3: Write config.json
    print("\n[3/5] Writing config.json...")
    config = dict(DEFAULT_CONFIG)
    if config_path and os.path.exists(config_path):
        with open(config_path) as f:
            user_config = json.load(f)
            config.update(user_config)
    config_json = json.dumps(config, indent=2, ensure_ascii=False)
    config_b64 = base64.b64encode(config_json.encode()).decode()
    cmd = (
        'powershell -Command "& {{'
        '$b64=\\"' + config_b64 + '\\";'
        '$bytes=[Convert]::FromBase64String($b64);'
        '[IO.File]::WriteAllBytes(\\"C:\\temp\\config.json\\",$bytes);'
        'if(Test-Path \\"C:\\temp\\config.json\\"){{Write-Host (\\"OK: \\" + (Get-Item \\"C:\\temp\\config.json\\").Length)}}"
        '}}"'
    )
    task_id = submit_task(node_id, cmd, timeout=30)
    time.sleep(5)
    result = get_result(task_id)
    if result.get("exit_code") == 0:
        print("  Config written: {} bytes".format(len(config_json)))
    else:
        print("  Config write failed: {}".format(result.get("stderr", "")[:200]))
        return False

    # Step 4: Kill old Gateway
    if existing_pid:
        print("\n[4/5] Killing old Gateway (PID {})...".format(existing_pid))
        task_id = submit_task(node_id, "taskkill /F /PID {}".format(existing_pid), timeout=10)
        time.sleep(3)
        result = get_result(task_id)
        print("  Kill result: {}".format(result.get("stdout", "").strip()[:100]))

    # Step 5: Start new Gateway
    print("\n[5/5] Starting new Gateway on port {}...".format(port))
    # Use the newest binary
    binary = binaries[-1] if binaries else "computehub.exe"
    cmd = 'cmd /c "start /B C:\\temp\\{} gateway --port {} --config C:\\temp\\config.json"'.format(binary, port)
    task_id = submit_task(node_id, cmd, timeout=15)
    time.sleep(5)

    # Verify
    task_id = submit_task(node_id, 'cmd /c "netstat -ano | findstr :{}"'.format(port), timeout=10)
    time.sleep(5)
    result = get_result(task_id)
    new_pid = None
    for line in result.get("stdout", "").split("\n"):
        if "LISTENING" in line:
            parts = line.strip().split()
            new_pid = parts[-1]
            break
    if new_pid:
        print("\n✅ Gateway started! PID: {}".format(new_pid))
        # Verify /ai
        task_id = submit_task(node_id, 'cmd /c "curl -s http://localhost:{}/ai > C:\\temp\\ai_verify.txt && type C:\\temp\\ai_verify.txt"'.format(port), timeout=10)
        time.sleep(5)
        result = get_result(task_id)
        if "AI 大厅" in result.get("stdout", ""):
            print("✅ /ai page: OK")
        else:
            print("⚠️  /ai page: check manually")
        return True
    else:
        print("\n❌ Gateway failed to start!")
        return False

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Deploy ComputeHub Gateway to Windows node")
    parser.add_argument("node_id", help="Windows node ID")
    parser.add_argument("--port", type=int, default=8282, help="Gateway port (default: 8282)")
    parser.add_argument("--config", help="Path to custom config.json")
    args = parser.parse_args()
    deploy_gateway(args.node_id, args.port, args.config)
