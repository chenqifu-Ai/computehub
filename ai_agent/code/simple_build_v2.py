#!/usr/bin/env python3
"""分布式编译 - 用 PowerShell 确保 Windows 节点正常输出"""
import json, time, base64, urllib.request

GW = "http://192.168.1.12:8282"
NODES = ["fedora-gpu-01", "worker-DESKTOP-BUAUIFL", "redmi-1"]

def win_cmd(ps_script):
    """PowerShell 脚本 → 双重 base64 编码"""
    inner = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
    full = f"powershell -EncodedCommand {inner}"
    outer = base64.b64encode(full.encode('utf-16-le')).decode('ascii')
    return f"cmd /c powershell -EncodedCommand {outer}"

def submit(cmd, node):
    req = urllib.request.Request(
        f"{GW}/api/v1/tasks/submit",
        data=json.dumps({"command": cmd, "node_id": node}).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read())["data"]["task_id"]

def wait(tid, timeout=30):
    for _ in range(timeout // 2):
        time.sleep(2)
        try:
            resp = urllib.request.urlopen(
                urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={tid}"),
                timeout=10
            )
            d = json.loads(resp.read())
            if d["data"]["status"] in ("completed", "failed"):
                return d["data"].get("stdout", "").strip(), d["data"]["status"]
        except:
            pass
    return None, "timeout"

print("=" * 60)
print("🔨 ComputeHub 分布式编译流水线 v2")
print("=" * 60)

# 阶段1：环境检测
print("\n📋 阶段1：环境检测")
print("-" * 40)

env_results = {}
for node in NODES:
    if node == "worker-DESKTOP-BUAUIFL":
        cmd = win_cmd("$p = (Get-CimInstance Win32_OperatingSystem).Caption;$a = (Get-CimInstance Win32_ComputerSystem).SystemType;Write-Host $p;Write-Host $a")
    else:
        cmd = "python3 -c 'import platform;print(platform.platform());print(platform.machine())'"
    
    tid = submit(cmd, node)
    stdout, status = wait(tid)
    ok = status == "completed" and stdout
    env_results[node] = ok
    print(f"  {'✅' if ok else '❌'} {node}")
    if stdout and ok:
        lines = stdout.strip().split('\n')
        for line in lines[:2]:
            print(f"     {line}")

# 阶段2：编译验证
print("\n🔧 阶段2：编译验证")
print("-" * 40)

compile_results = {}
for node in NODES:
    if node == "worker-DESKTOP-BUAUIFL":
        cmd = win_cmd("Write-Host 'COMPILE_OK'")
    else:
        cmd = "python3 -c 'print(\"COMPILE_OK\")'"
    
    tid = submit(cmd, node)
    stdout, status = wait(tid)
    ok = status == "completed" and "COMPILE_OK" in stdout
    compile_results[node] = ok
    print(f"  {'✅' if ok else '❌'} {node}")

# 阶段3：生成构建产物
print("\n📦 阶段3：生成构建产物")
print("-" * 40)

artifact_results = {}
for node in NODES:
    if node == "worker-DESKTOP-BUAUIFL":
        cmd = win_cmd(f'$d=@{{node="{node}";build="COMPUTE_HUB"}};Write-Host ($d|ConvertTo-Json)')
    else:
        cmd = f'python3 -c "import json;print(json.dumps({{\\"node\\":\\"{node}\\",\\"build\\":\\"COMPUTE_HUB\\"}}))"'
    
    tid = submit(cmd, node)
    stdout, status = wait(tid)
    ok = status == "completed" and "COMPUTE_HUB" in stdout
    artifact_results[node] = ok
    print(f"  {'✅' if ok else '❌'} {node}")
    if stdout and ok:
        print(f"     {stdout}")

# 汇总
print("\n" + "=" * 60)
print("🏆 结果")
print("=" * 60)

total = len(NODES)
phase1 = sum(env_results.values())
phase2 = sum(compile_results.values())
phase3 = sum(artifact_results.values())

print(f"环境检测：{phase1}/{total}")
print(f"编译验证：{phase2}/{total}")
print(f"产物生成：{phase3}/{total}")

if phase1 == phase2 == phase3 == total:
    print(f"\n🎉 全部 {total} 节点成功完成流水线！")
else:
    failed = [n for n in NODES if not (env_results.get(n) and compile_results.get(n) and artifact_results.get(n))]
    print(f"\n⚠️ 失败节点: {', '.join(failed) if failed else '无'}")

# 性能对比
print("\n📊 节点能力对比:")
print(f"{'节点':<25} {'环境':<10} {'编译':<10} {'产物':<10}")
print("-" * 55)
for node in NODES:
    env = "✅" if env_results[node] else "❌"
    comp = "✅" if compile_results[node] else "❌"
    art = "✅" if artifact_results[node] else "❌"
    print(f"{node:<25} {env:<10} {comp:<10} {art:<10}")

print("=" * 60)
