#!/usr/bin/env python3
"""
RTX 4060 节点重启脚本 — 通过 ComputeHub 任务下发远程重启 wanlida-opc01 worker
"""
import subprocess, json, time, sys

GATEWAY_CMD = ['ssh', '-i', '/root/.ssh/id_ed25519_computehub', '-p', '8022', 'computehub@36.250.122.43']

def submit_task(cmd_str, node_id='wanlida-opc01', timeout=60):
    payload = {'type': 'shell', 'command': cmd_str, 'node_id': node_id, 'timeout': timeout}
    data = json.dumps(payload).encode()
    proc = subprocess.Popen(
        GATEWAY_CMD + ['curl', '-s', '-X', 'POST', 'http://127.0.0.1:8282/api/v1/tasks/submit', '-H', 'Content-Type: application/json', '-d', '@-'],
        stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, _ = proc.communicate(input=data)
    return json.loads(out)

def wait_result(task_id, timeout=60):
    """轮询获取任务结果"""
    start = time.time()
    while time.time() - start < timeout:
        proc = subprocess.Popen(
            GATEWAY_CMD + ['curl', '-s', '-X', 'POST', 'http://127.0.0.1:8282/api/v1/tasks/result', '-H', 'Content-Type: application/json', '-d', '@-'],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
        )
        out, _ = proc.communicate(json.dumps({"task_id": task_id}).encode())
        data = json.loads(out)
        if not data.get("success") and "not found" in data.get("error", ""):
            time.sleep(5)
            continue
        return data
        time.sleep(5)
    return None

def list_nodes():
    """获取节点列表"""
    proc = subprocess.Popen(
        GATEWAY_CMD + ['curl', '-s', 'http://127.0.0.1:8282/api/v1/nodes/list'],
        stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    out, _ = proc.communicate()
    return json.loads(out)

def main():
    print("=" * 60)
    print("🔄 RTX 4060 节点重启 — wanlida-opc01")
    print("=" * 60)

    # Step 1: 确认 GPU 状态
    print("\n📊 Step 1: 确认 GPU 状态...")
    r = submit_task('nvidia-smi --query-gpu=name,memory.total,memory.used,temperature.gpu --format=csv')
    if r.get('success'):
        tid = r['data']['task_id']
        res = wait_result(tid, 30)
        if res and res.get('success'):
            stdout = res.get('data', {}).get('stdout', '')
            for line in stdout.strip().split('\n'):
                if line and 'NVIDIA' in line:
                    print(f"  ✅ {line.strip()}")
                    break
            else:
                print(f"  ✅ {stdout.strip()[:200]}")
        else:
            print(f"  ⚠️  结果: {res}")
    else:
        print(f"  ❌ 提交失败: {r}")
        sys.exit(1)

    # Step 2: 查找 worker binary
    print("\n🔍 Step 2: 查找 worker binary...")
    # PowerShell: 递归搜索多个常见路径
    ps_find = (
        '$paths = @('
        '"C:\\OpenClaw\\worker\\computehub.exe",'
        '"C:\\OpenClaw\\worker\\compute-worker.exe",'
        '"C:\\computehub\\computehub.exe",'
        '"C:\\workers\\computehub.exe",'
        '"D:\\OpenClaw\\worker\\computehub.exe",'
        '"D:\\computehub\\computehub.exe",'
        '"C:\\OPC\\deploy\\computehub.exe",'
        '"C:\\Program Files\\OpenClaw\\computehub.exe",'
        '"C:\\Program Files\\OpenClaw\\worker\\computehub.exe"'
        '); '
        'foreach ($p in $paths) { if (Test-Path $p) { Write-Output "FOUND:$p"; exit 0 } }; '
        'Write-Output "NOT_FOUND"; exit 0'
    )
    r = submit_task(f'powershell -NoProfile -Command "{ps_find}"')
    if r.get('success'):
        tid = r['data']['task_id']
        res = wait_result(tid, 30)
        if res and res.get('success'):
            stdout = res.get('data', {}).get('stdout', '')
            for line in stdout.strip().split('\n'):
                if 'FOUND:' in line:
                    binary_path = line.split('FOUND:')[1]
                    print(f"  ✅ Found binary: {binary_path}")
                elif line.strip():
                    print(f"  {line.strip()}")
            # 下一步用这个路径
            found_binary = None
            for line in stdout.strip().split('\n'):
                if 'FOUND:' in line:
                    found_binary = line.split('FOUND:')[1]
                    break
        else:
            print(f"  ⚠️  结果: {res}")
    else:
        print(f"  ❌ 提交失败: {r}")
        sys.exit(1)

    # Step 3: 重启 worker
    print("\n🔄 Step 3: 重启 worker 带 GPU 参数...")
    if not found_binary:
        print("  ⚠️  未找到 binary，尝试通用路径...")
        found_binary = "C:\\OpenClaw\\worker\\computehub.exe"

    # 重启脚本：kill old → wait → start new with GPU params
    ps_restart = (
        f'Write-Host "[restart] Killing old worker..."; '
        f'Get-Process computehub-worker -ErrorAction SilentlyContinue | Stop-Process -Force; '
        f'Get-Process compute-worker -ErrorAction SilentlyContinue | Stop-Process -Force; '
        f'Start-Sleep -Seconds 5; '
        f'Write-Host "[restart] Starting new worker..."; '
        f'Start-Process -FilePath "{found_binary}" '
        f'-ArgumentList "worker --gw http://36.250.122.43:8282 --node-id wanlida-opc01 --gpu-type RTX-4060 --gpu 1 --concurrent 8 --region cn-east" '
        f'-WindowStyle Hidden; '
        f'Write-Host "[restart] Done. Binary: {found_binary}"'
    )
    
    r = submit_task(f'powershell -NoProfile -Command "{ps_restart}"')
    if r.get('success'):
        tid = r['data']['task_id']
        print(f"  ✅ 重启任务已提交: {tid}")
        res = wait_result(tid, 60)
        if res and res.get('success'):
            stdout = res.get('data', {}).get('stdout', '')
            print(f"  输出: {stdout.strip()}")
    else:
        print(f"  ❌ 提交失败: {r}")

    # Step 4: 等待 30 秒让 worker 完成重启，然后验证
    print("\n⏳ 等待 30 秒让 worker 完成重启...")
    time.sleep(30)

    print("\n📊 Step 4: 验证节点状态...")
    data = list_nodes()
    for n in data.get('data', []):
        nid = n.get('node_id', '?')
        gpu = n.get('gpu_type', 'CPU')
        status = n.get('status', '?')
        ver = n.get('version', '?')
        temp = n.get('temperature', 0)
        active = n.get('active_tasks', 0)
        marker = " ⭐ RTX 4060" if nid == 'wanlida-opc01' else ""
        print(f"  Node: {nid}{marker}")
        print(f"    GPU: {gpu} | Status: {status} | Ver: {ver} | Temp: {temp}°C | Tasks: {active}")

    print("\n✅ 重启流程完成！")
    print("  如果 GPU 类型仍显示为空，可能需要等下一个心跳周期（~10s）上报")

if __name__ == "__main__":
    main()
