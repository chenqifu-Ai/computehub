#!/usr/bin/env python3
"""
wanlida-opc01 综合测试脚本
目标：通过exec_shell下发任务到 wanlida-opc01，测试各项能力
"""

import json
import subprocess
import sys

GATEWAY = "http://localhost:8282"

def send_task(task_type, params):
    """通过API发送任务到wanlida-opc01"""
    payload = {
        "node_id": "wanlida-opc01",
        "task_type": task_type,
        "params": params
    }
    result = subprocess.run(
        ["curl", "-s", "-m", "30", "-X", "POST",
         f"{GATEWAY}/api/v2/tasks",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload)],
        capture_output=True, text=True
    )
    return json.loads(result.stdout) if result.stdout else {}

def exec_shell(node_id, command, timeout=60):
    """通过API执行远程命令"""
    payload = {
        "node_id": node_id,
        "task_type": "exec_shell",
        "params": {
            "command": command,
            "timeout": timeout
        }
    }
    result = subprocess.run(
        ["curl", "-s", "-m", "65", "-X", "POST",
         f"{GATEWAY}/api/v2/tasks",
         "-H", "Content-Type: application/json",
         "-d", json.dumps(payload)],
        capture_output=True, text=True
    )
    return json.loads(result.stdout) if result.stdout else {}

def run_tests():
    node_id = "wanlida-opc01"
    results = []
    
    print("=" * 60)
    print(f"🧪 wanlida-opc01 综合测试套件")
    print(f"🖥️  GPU: RTX 4060 | CPU: 24核 | Windows/amd64")
    print("=" * 60)
    
    # 测试1: 基础信息
    print("\n📋 测试1: 基础系统信息")
    r = exec_shell(node_id, "systeminfo | findstr /C:\"OS\" /C:\"Processor\" /C:\"Total Physical Memory\"")
    print(f"  输出: {r.get('result', r)}")
    results.append(("基础信息", r))
    
    # 测试2: GPU检测（重点！看能否修正10卡bug）
    print("\n🎮 测试2: GPU真实检测")
    r = exec_shell(node_id, 
        "nvidia-smi --query-gpu=index,name,temperature.gpu,memory.used,memory.total,utilization.gpu --format=csv,noheader",
        timeout=15)
    print(f"  输出: {r.get('result', r)}")
    results.append(("GPU检测", r))
    
    # 测试3: Python环境
    print("\n🐍 测试3: Python环境")
    r = exec_shell(node_id, "python --version 2>&1 & python3 --version 2>&1", timeout=10)
    print(f"  输出: {r.get('result', r)}")
    results.append(("Python环境", r))
    
    # 测试4: Git环境
    print("\n📦 测试4: Git环境")
    r = exec_shell(node_id, "git --version", timeout=10)
    print(f"  输出: {r.get('result', r)}")
    results.append(("Git环境", r))
    
    # 测试5: 磁盘信息
    print("\n💾 测试5: 磁盘信息")
    r = exec_shell(node_id, "wmic logicaldisk get caption,freespace,totalsize /format:list")
    print(f"  输出: {r.get('result', r)}")
    results.append(("磁盘信息", r))
    
    # 测试6: 网络延迟
    print("\n🌐 测试6: 网络延迟测试")
    r = exec_shell(node_id, "ping -n 4 36.250.122.43", timeout=15)
    print(f"  输出: {r.get('result', r)}")
    results.append(("网络延迟", r))
    
    # 测试7: 文件上传下载（Gallery）
    print("\n📤 测试7: Gallery文件能力")
    r = exec_shell(node_id, 
        "echo test_content > C:\\temp\\test.txt 2>nul & if exist C:\\temp\\test.txt (type C:\\temp\\test.txt & del C:\\temp\\test.txt & echo OK) else (echo FAIL)",
        timeout=15)
    print(f"  输出: {r.get('result', r)}")
    results.append(("文件IO", r))
    
    # 测试8: GPU计算（Python小测试）
    print("\n🔢 测试8: GPU计算能力（小负载）")
    r = exec_shell(node_id,
        "python -c \"import torch; print('PyTorch CUDA:', torch.cuda.is_available()); print('GPU count:', torch.cuda.device_count())\" 2>&1 || echo 'PyTorch not installed'",
        timeout=30)
    print(f"  输出: {r.get('result', r)}")
    results.append(("GPU计算", r))
    
    # 测试9: Go环境（如果有）
    print("\n🔧 测试9: Go环境")
    r = exec_shell(node_id, "go version 2>&1 || echo 'Go not installed'", timeout=10)
    print(f"  输出: {r.get('result', r)}")
    results.append(("Go环境", r))
    
    # 测试10: 环境变���
    print("\n🌍 测试10: 环境变量")
    r = exec_shell(node_id, "set")
    print(f"  输出: {r.get('result', r)[:500]}...")
    results.append(("环境变量", r))
    
    # 汇总
    print("\n" + "=" * 60)
    print("📊 测试汇总:")
    for name, r in results:
        status = "✅" if r.get("status") == "success" else "❌"
        print(f"  {status} {name}: {r.get('status', 'unknown')}")
    print("=" * 60)
    
    return results

if __name__ == "__main__":
    run_tests()
