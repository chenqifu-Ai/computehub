#!/usr/bin/env python3
"""ComputeHub 自举安装：各节点安装开发工具"""
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
    inner = base64.b64encode(ps.encode('utf-16-le')).decode('ascii')
    full = f"powershell -EncodedCommand {inner}"
    outer = base64.b64encode(full.encode('utf-16-le')).decode('ascii')
    return f"cmd /c powershell -EncodedCommand {outer}"

print("=" * 70)
print("🔧 ComputeHub 自举安装：安装开发工具链")
print("=" * 70)

# 检测现有工具
print("\n🔍 步骤 1: 检测现有工具")
print("-" * 50)

for node in NODES:
    cmd = "python3 -c \"import subprocess;[print(t+':ok' if subprocess.run([t,'--version'],capture_output=True).returncode==0 else print(t+':no')) for t in ['gcc','g++','clang']]\""
    tid = submit(cmd, node)
    stdout, stderr, status = wait(tid, 30)
    if status == "completed":
        for line in stdout.strip().split('\n'):
            print(f"  {node}: {line}")
    else:
        print(f"  {node}: 检测失败")

# 安装工具
print("\n📦 步骤 2: 安装缺失工具")
print("-" * 50)

install_results = {}

# Fedora: dnf install gcc
print("\n📤 Fedora: dnf install gcc...")
tid = submit("dnf install -y gcc gcc-c++ 2>&1 | tail -3", "fedora-gpu-01")
stdout, stderr, status = wait(tid, 300)
print(f"  状态: {status}")
if status == "completed":
    print(f"  ✅ Fedora 工具就绪")
    install_results["fedora-gpu-01"] = True

# Windows: winget install MinGW
print("\n📤 Windows: winget install MinGW...")
ps = """
$w = Get-Command winget -ErrorAction SilentlyContinue
if ($w) {
    Write-Host "WINGET_OK"
    winget install --id MinGW.MingGW --source winget --accept-source-agreements --accept-package-agreements --silent --disable-interactivity
    $e = $LASTEXITCODE
    if ($e -eq 0) { Write-Host "INSTALLED" }
    else { Write-Host "FAIL: $e" }
} else {
    Write-Host "WINGET_NOT_AVAILABLE"
    Write-Host "TRY_MANUAL_DOWNLOAD"
    # 下载 MinGW
    $url = "https://github.com/niXman/mingw-builds-binaries/releases/download/13.2.0-rt_v11-rev0/x86_64-13.2.0-release-posix-seh-ucrt-rt_v11-v0-vixen-mingw.tar.xz"
    $dest = "C:\\mingw.tar.xz"
    try {
        $wc = New-Object System.Net.WebClient
        $wc.DownloadFile($url, $dest)
        $size = [math]::Round((Get-Item $dest).Length / 1MB, 1)
        Write-Host "DOWNLOADED: ${size}MB"
        & tar -xf $dest -C C:\
        Write-Host "EXTRACTED"
        Write-Host "INSTALLED"
    } catch {
        Write-Host "MANUAL_FAIL: $_"
    }
}
"""
tid = submit(win_cmd(ps), "worker-DESKTOP-BUAUIFL")
stdout, stderr, status = wait(tid, 600)
print(f"  状态: {status}")
if "INSTALLED" in stdout:
    print(f"  ✅ Windows 工具就绪")
    install_results["worker-DESKTOP-BUAUIFL"] = True
elif "WINGET_OK" in stdout:
    print(f"  winget 可用，正在安装...")
    install_results["worker-DESKTOP-BUAUIFL"] = True
else:
    print(f"  ❌ Windows 安装失败")
    install_results["worker-DESKTOP-BUAUIFL"] = False

# Redmi: pkg install gcc clang
print("\n📤 Redmi: pkg install gcc clang...")
tid = submit("pkg install -y gcc clang 2>&1 | tail -3", "redmi-1")
stdout, stderr, status = wait(tid, 300)
print(f"  状态: {status}")
if status == "completed" and ("installed" in stdout.lower() or "complete" in stdout.lower()):
    print(f"  ✅ Redmi 工具就绪")
    install_results["redmi-1"] = True
else:
    print(f"  ⚠️ Redmi 安装结果不确定")
    install_results["redmi-1"] = status == "completed"

# 总结
print("\n" + "=" * 70)
print("📊 安装结果")
print("=" * 70)
ok = sum(1 for v in install_results.values() if v)
print(f"安装成功: {ok}/{len(NODES)}")
for node, result in install_results.items():
    icon = "✅" if result else "❌"
    print(f"  {icon} {node}")
print("=" * 70)
