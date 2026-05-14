#!/usr/bin/env python3
"""ComputeHub 分布式编译: 源码分发 → 各节点编译 → 收集产物"""
import json, time, base64, urllib.request

GW = "http://192.168.1.12:8282"
NODES = ["fedora-gpu-01", "worker-DESKTOP-BUAUIFL", "redmi-1"]

def submit(cmd, node):
    req = urllib.request.Request(
        f"{GW}/api/v1/tasks/submit",
        data=json.dumps({"command": cmd, "node_id": node}).encode(),
        headers={"Content-Type": "application/json"},
    )
    resp = urllib.request.urlopen(req, timeout=10)
    return json.loads(resp.read())["data"]["task_id"]

def wait(tid, timeout=90):
    for _ in range(timeout // 2):
        time.sleep(2)
        try:
            d = json.loads(urllib.request.urlopen(
                urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={tid}")
            ).read())
            if d["data"]["status"] in ("completed", "failed"):
                return d["data"].get("stdout", ""), d["data"].get("stderr", ""), d["data"]["status"]
        except:
            pass
    return "", "", "timeout"

print("=" * 70)
print("🔨 COMPUTEHUB 分布式编译流水线")
print("=" * 70)

# C 源码
C_SOURCE = "#include <stdio.h>\nint main(){printf(\"COMPUTE_HUB_BUILD\\n\");return 0;}"
b64_src = base64.b64encode(C_SOURCE.encode()).decode()

# ===== 1. 检测工具链 =====
print("\n🔍 步骤1: 检测各节点编译工具")
print("-" * 50)

tool_info = {}
for node in NODES:
    cmd = "python3 -c \"import subprocess;[print(t+':'+subprocess.run([t,'--version'],capture_output=True,text=True,timeout=3).stdout.split(chr(10))[0][:50] if subprocess.run([t,'--version'],capture_output=True).returncode==0 else print(t+':not-found')) for t in ['gcc','clang','python3','python']]\""
    tid = submit(cmd, node)
    stdout, stderr, status = wait(tid, 30)
    ok = status == "completed" and stdout
    tool_info[node] = ok
    print(f"  {'✅' if ok else '❌'} {node}")
    if ok:
        for line in stdout.strip().split('\n'):
            print(f"     {line}")

# ===== 2. 编译 =====
print("\n📦 步骤2: 源码分发 → 编译")
print("-" * 50)

compile_results = {}

for node in NODES:
    print(f"\n📤 {node}...", end=" ", flush=True)
    
    if node == "fedora-gpu-01":
        cmd = f"echo '{b64_src}' | base64 -d > /tmp/b.c && gcc -O2 -o /tmp/b /tmp/b.c && /tmp/b && rm /tmp/b.c /tmp/b"
    elif node == "worker-DESKTOP-BUAUIFL":
        # Windows: write file with certutil, compile with cl or gcc
        ps = f"""
$source = "{b64_src}"
$bytes = [System.Convert]::FromBase64String($source)
[System.IO.File]::WriteAllBytes("C:\\\\b.c", $bytes)
$result = "COMPILE_FAIL"
$r = Start-Process gcc -ArgumentList "-O2", "-o", "C:\\\\b.exe", "C:\\\\b.c" -NoNewWindow -Wait -PassThru -ErrorAction SilentlyContinue
if ($r -and $r.ExitCode -eq 0) {{
    $r2 = Start-Process "C:\\\\b.exe" -NoNewWindow -Wait -RedirectStandardOutput "C:\\\\out.txt"
    if (Test-Path "C:\\\\out.txt") {{ Get-Content "C:\\\\out.txt" }}
    $result = "COMPILE_SUCCESS"
}}
foreach ($f in @("C:\\\\b.c","C:\\\\b.exe","C:\\\\out.txt")) {{ if (Test-Path $f) {{ Remove-Item $f -Force }} }}
Write-Host "RESULT=$result"
"""
        inner_b64 = base64.b64encode(ps.encode('utf-16-le')).decode('ascii')
        full = f"powershell -EncodedCommand {inner_b64}"
        outer_b64 = base64.b64encode(full.encode('utf-16-le')).decode('ascii')
        cmd = f"cmd /c powershell -EncodedCommand {outer_b64}"
    else:
        cmd = f"echo '{b64_src}' | base64 -d > /tmp/b.c && clang -O2 -o /tmp/b /tmp/b.c && /tmp/b && rm /tmp/b.c /tmp/b"
    
    tid = submit(cmd, node)
    stdout, stderr, status = wait(tid, 90)
    
    if status == "completed" and "COMPILE_SUCCESS" in stdout:
        compile_results[node] = True
        print("✅ 编译成功")
    elif status == "completed" and "COMPUTE_HUB_BUILD" in stdout:
        compile_results[node] = True
        print("✅ 编译成功")
    elif status == "completed":
        compile_results[node] = False
        print("⚠️ 编译失败")
        if stdout:
            for line in stdout.strip().split('\n')[:3]:
                print(f"     {line}")
        if stderr:
            print(f"     err: {stderr[:100]}")
    else:
        compile_results[node] = False
        print(f"❌ ({status})")

# ===== 结果 =====
print("\n" + "=" * 70)
print("📊 编译结果")
print("=" * 70)

ok_count = sum(1 for v in compile_results.values() if v)
print(f"✅ 成功: {ok_count}/{len(NODES)}")
print(f"❌ 失败: {len(NODES) - ok_count}/{len(NODES)}")

for node in NODES:
    icon = "✅" if compile_results[node] else "❌"
    print(f"  {icon} {node}")

print("\n" + "=" * 70)
if ok_count == len(NODES):
    print("🎉 分布式编译全部成功！")
else:
    print(f"⚠️ {ok_count}/{len(NODES)} 节点成功")
print("=" * 70)
