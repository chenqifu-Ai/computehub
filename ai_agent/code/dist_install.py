#!/usr/bin/env python3
"""
🔨 ComputeHub 自举安装 + 分布式编译
通过 Gateway 调度各节点安装工具 → 编译 → 收集产物
"""
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

def wait(tid, timeout=300):
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

def win_cmd(ps):
    """PowerShell 双重 base64 编码"""
    inner = base64.b64encode(ps.encode('utf-16-le')).decode('ascii')
    full = f"powershell -EncodedCommand {inner}"
    outer = base64.b64encode(full.encode('utf-16-le')).decode('ascii')
    return f"cmd /c powershell -EncodedCommand {outer}"

print("=" * 70)
print("🔧 COMPUTEHUB 自举安装 + 分布式编译")
print("=" * 70)
print("策略: Gateway 调度 → 各节点安装工具 → 编译 → 收集产物")
print("=" * 70)

# ===== 步骤 1: 检测现有工具 =====
print("\n🔍 步骤 1: 检测现有工具链")
print("-" * 50)

for node in NODES:
    if node == "fedora-gpu-01":
        cmd = "python3 -c \"import subprocess;[print(t+':'+subprocess.run([t,'--version'],capture_output=True,text=True,timeout=3).stdout.split(chr(10))[0][:50] if subprocess.run([t,'--version'],capture_output=True).returncode==0 else print(t+':not-found')) for t in ['gcc','g++','clang']]\""
    elif node == "worker-DESKTOP-BUAUIFL":
        ps = '''
foreach ($t in @("gcc","g++","clang","python")) {
    try {
        $r = Start-Process $t -ArgumentList "--version" -NoNewWindow -PassThru -Wait -RedirectStandardOutput "C:\${t}_v.txt" -ErrorAction SilentlyContinue
        if (Test-Path "C:\${t}_v.txt") {
            $ver = (Get-Content "C:\${t}_v.txt")[0]
            Write-Host "${t}:${ver}"
            Remove-Item "C:\${t}_v.txt"
        } else {
            Write-Host "${t}:not-found"
        }
    } catch {
        Write-Host "${t}:not-found"
    }
}
'''
        cmd = win_cmd(ps)
    else:
        cmd = "python3 -c \"import subprocess;[print(t+':'+subprocess.run([t,'--version'],capture_output=True,text=True,timeout=3).stdout.split(chr(10))[0][:50] if subprocess.run([t,'--version'],capture_output=True).returncode==0 else print(t+':not-found')) for t in ['gcc','g++','clang']]\""
    
    tid = submit(cmd, node)
    stdout, stderr, status = wait(tid, 30)
    print(f"\n  {node}:")
    if status == "completed":
        for line in stdout.strip().split('\n'):
            if line.strip():
                tool, ver = line.split(':', 1)
                print(f"    {'✅' if 'not-found' not in ver else '❌'} {tool}")
    else:
        print(f"    检测失败")

# ===== 步骤 2: 安装缺失工具 =====
print("\n" + "=" * 70)
print("📦 步骤 2: 安装缺失工具")
print("=" * 70)

# Fedora: 用 dnf 安装 gcc
print("\n📤 Fedora 节点 (fedora-gpu-01)...")
cmd = "dnf install -y gcc gcc-c++ 2>&1 | tail -3"
tid = submit(cmd, "fedora-gpu-01")
stdout, stderr, status = wait(tid, 300)
if status == "completed" and ("Installed" in stdout or "Complete" in stdout):
    print("  ✅ gcc 安装完成")
else:
    print(f"  状态: {status}")
    for line in (stdout + stderr).split('\n')[-3:]:
        if line.strip():
            print(f"     {line.strip()[:80]}")

# Windows: 用 winget 安装 MinGW
print("\n📤 Windows 节点 (worker-DESKTOP-BUAUIFL)...")
ps_script = """
# 检查 winget
$wingetAvailable = Get-Command winget -ErrorAction SilentlyContinue

if ($wingetAvailable) {
    Write-Host "WINGET_AVAILABLE"
    # 安装 MinGW-w64
    $r = winget install --id MinGW.MingGW --source winget --accept-source-agreements --accept-package-agreements --silent --disable-interactivity
    if ($LASTEXITCODE -eq 0) {
        Write-Host "MINGW_INSTALLED"
        # 验证
        $v = Start-Process gcc -ArgumentList "--version" -NoNewWindow -Wait -RedirectStandardOutput "C:\gcc_v.txt" -ErrorAction SilentlyContinue
        if (Test-Path "C:\gcc_v.txt") {
            Write-Host "GCC_VER:"
            Get-Content "C:\gcc_v.txt"
        }
    } else {
        Write-Host "WINGET_INSTALL_FAIL: exit $LASTEXITCODE"
    }
} else {
    Write-Host "WINGET_NOT_AVAILABLE"
    # 手动下载 MinGW
    Write-Host "DOWNLOADING..."
    $url = "https://github.com/niXman/mingw-builds-binaries/releases/download/13.2.0-rt_v11-rev0/x86_64-13.2.0-release-posix-seh-ucrt-rt_v11-v0-vixen-mingw.tar.xz"
    $dest = "C:\mingw.tar.xz"
    try {
        $wc = New-Object System.Net.WebClient
        $wc.DownloadFile($url, $dest)
        $size = [math]::Round((Get-Item $dest).Length / 1MB, 1)
        Write-Host "DOWNLOAD_DONE: ${size}MB"
        
        # 解压
        Write-Host "EXTRACTING..."
        & 7z x $dest -oC:\ -y
        Write-Host "EXTRACT_DONE"
        
        # 添加 PATH
        $mingwDir = Get-ChildItem C:\ | Where-Object { $_.Name -like "x86_64*" } | Select-Object -First 1
        if ($mingwDir) {
            $env:Path += ";C:\$($mingwDir.Name)\mingw64\bin"
            [Environment]::SetEnvironmentVariable("Path", $env:Path, "Machine")
        }
        
        Write-Host "MINGW_INSTALLED"
    } catch {
        Write-Host "INSTALL_FAIL: $($_.Exception.Message)"
    }
}
"""
inner = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
full = f"powershell -EncodedCommand {inner}"
outer = base64.b64encode(full.encode('utf-16-le')).decode('ascii')
cmd = f"cmd /c powershell -EncodedCommand {outer}"

tid = submit(cmd, "worker-DESKTOP-BUAUIFL")
stdout, stderr, status = wait(tid, 600)
print(f"  状态: {status}")
for line in stdout.strip().split('\n'):
    if 'WINGET' in line or 'MINGW' in line or 'DOWNLOAD' in line or 'EXTRACT' in line or 'GCC_VER' in line or 'INSTALL' in line:
        print(f"     {line}")

# Redmi: 用 pkg 安装 gcc/clang
print("\n📤 Redmi 节点 (redmi-1)...")
cmd = "pkg install -y gcc clang 2>&1 | tail -3"
tid = submit(cmd, "redmi-1")
stdout, stderr, status = wait(tid, 300)
if status == "completed" and ("Installed" in stdout or "Complete" in stdout):
    print("  ✅ gcc/clang 安装完成")
else:
    print(f"  状态: {status}")
    for line in (stdout + stderr).split('\n')[-3:]:
        if line.strip():
            print(f"     {line.strip()[:80]}")

# ===== 步骤 3: 分布式编译 =====
print("\n" + "=" * 70)
print("🔨 步骤 3: 分布式编译")
print("=" * 70)

# C 程序源码
C_SOURCE = """
#include <stdio.h>
int main() {
    printf("╔══════════════════════════════════════╗\\n");
    printf("║   ComputeHub Distributed Build Test  ║\\n");
    printf("║   Status: SUCCESS                    ║\\n");
    printf("╚══════════════════════════════════════╝\\n");
    return 0;
}
"""

b64_source = base64.b64encode(C_SOURCE.encode()).decode()

build_results = {}

for node in NODES:
    print(f"\n📤 {node} 编译...")
    
    if node == "fedora-gpu-01":
        cmd = f"""
echo '{b64_source}' | base64 -d > /tmp/hello.c
gcc -O2 -o /tmp/hello /tmp/hello.c && /tmp/hello
rm -f /tmp/hello.c /tmp/hello
"""
    elif node == "worker-DESKTOP-BUAUIFL":
        ps = f"""
$source = "{b64_source}"
$bytes = [System.Convert]::FromBase64String($source)
[System.IO.File]::WriteAllBytes("C:\\\\hello.c", $bytes)

$result = "BUILD_FAIL"
$r = Start-Process gcc -ArgumentList "-O2", "-o", "C:\\\\hello.exe", "C:\\\\hello.c" -NoNewWindow -Wait -PassThru -ErrorAction SilentlyContinue
if ($r -and $r.ExitCode -eq 0) {{
    Start-Process "C:\\\\hello.exe" -NoNewWindow -Wait -RedirectStandardOutput "C:\\\\out.txt"
    if (Test-Path "C:\\\\out.txt") {{
        Get-Content "C:\\\\out.txt"
    }}
    $result = "BUILD_SUCCESS"
}}

foreach ($f in @("C:\\\\hello.c", "C:\\\\hello.exe", "C:\\\\out.txt")) {{
    if (Test-Path $f) {{ Remove-Item $f -Force }}
}}
Write-Host "BUILD_STATUS=$result"
"""
        inner = base64.b64encode(ps.encode('utf-16-le')).decode('ascii')
        full = f"powershell -EncodedCommand {inner}"
        outer = base64.b64encode(full.encode('utf-16-le')).decode('ascii')
        cmd = f"cmd /c powershell -EncodedCommand {outer}"
    else:
        cmd = f"""
echo '{b64_source}' | base64 -d > /tmp/hello.c
clang -O2 -o /tmp/hello /tmp/hello.c && /tmp/hello
rm -f /tmp/hello.c /tmp/hello
"""
    
    tid = submit(cmd, node)
    stdout, stderr, status = wait(tid, 120)
    
    if status == "completed" and "SUCCESS" in stdout:
        build_results[node] = {"ok": True, "stdout": stdout}
        print(f"  ✅ 编译成功")
    elif status == "completed":
        build_results[node] = {"ok": False, "stdout": stdout[:300], "stderr": stderr[:200]}
        print(f"  ⚠️ 编译失败")
        if stdout:
            for line in stdout.strip().split('\n')[:3]:
                print(f"     {line}")
    else:
        build_results[node] = {"ok": False, "status": status}
        print(f"  ❌ 超时 ({status})")

# ===== 总结 =====
print("\n" + "=" * 70)
print("🏆 分布式编译总结")
print("=" * 70)

success = [n for n, r in build_results.items() if r.get("ok")]
failed = [n for n, r in build_results.items() if not r.get("ok")]

print(f"\n✅ 编译成功: {len(success)}/{len(NODES)}")
print(f"❌ 编译失败: {len(failed)}/{len(NODES)}")

for node in NODES:
    r = build_results[node]
    icon = "✅" if r.get("ok") else "❌"
    print(f"\n  {icon} {node}")
    if r.get("ok"):
        for line in r["stdout"].strip().split('\n'):
            if '╔' in line or '║' in line or '═' in line or '╝' in line:
                print(f"     {line}")

print("\n" + "=" * 70)
if len(success) == len(NODES):
    print("🎉 全部节点成功完成分布式编译！")
else:
    print(f"⚠️ {len(success)}/{len(NODES)} 节点成功")
print("=" * 70)
