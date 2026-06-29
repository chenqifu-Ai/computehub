#!/usr/bin/env python3
"""Clean install: ZIP-based Node.js + OpenClaw on Windows"""
import requests, sys, time, json

GW = "http://36.250.122.43:8282"
node = "windows-mobile"

def submit(cmd, timeout=300):
    r = requests.post(f"{GW}/api/v1/tasks/submit", json={
        "node_id": node, "command": cmd, "timeout": timeout
    })
    tid = r.json()["data"]["task_id"]
    print(f"  -> {tid}")
    return tid

def wait(tid, timeout=300):
    start = time.time()
    while time.time() - start < timeout:
        r = requests.get(f"{GW}/api/v1/tasks/detail?task_id={tid}", timeout=10)
        d = r.json().get("data", {})
        st = d.get("status", "")
        if st in ("completed", "failed"):
            return d
        try:
            pr = requests.get(f"{GW}/api/v1/tasks/progress?task_id={tid}", timeout=5)
            pd = pr.json().get("data", {})
            so = pd.get("stdout", "")
            lines = [l for l in so.split("\n") if l.strip()]
            if lines:
                print(f"  ... {lines[-1][:120]}")
        except:
            pass
        time.sleep(5)
    return None

# Step 1: Clean old install files
print("=== Step 1: Clean old files ===")
tid = submit("del C:\\installers\\install.ps1 C:\\installers\\node-v24.16.0-x64.msi C:\\installers\\nodejs.zip 2>nul & echo CLEAN_DONE", 30)
d = wait(tid)
print(f"  {d.get('stdout','')[:100] if d else 'timeout'}")

# Step 2: Download fresh install.ps1 (ZIP version)
print("=== Step 2: Download install.ps1 ===")
tid = submit("powershell -Command \"(new-object net.webclient).downloadfile('http://36.250.122.43:8282/api/v1/files/install.ps1','C:\\installers\\install.ps1')\"", 60)
d = wait(tid)
print(f"  exit={d.get('exit_code') if d else 'timeout'}")

# Step 3: Download nodejs.zip (36MB)
print("=== Step 3: Download nodejs.zip ===")
# certutil is more reliable for large files
tid = submit("certutil -urlcache -split -f http://36.250.122.43:8282/api/v1/files/nodejs.zip C:\\installers\\nodejs.zip", 300)
d = wait(tid, timeout=300)
if d and d.get("exit_code") == 0:
    print(f"  OK (certutil)")
elif d:
    print(f"  exit={d.get('exit_code')}")
    # Try PowerShell as fallback
    print("  retry with PowerShell...")
    tid = submit("powershell -Command \"(new-object net.webclient).downloadfile('http://36.250.122.43:8282/api/v1/files/nodejs.zip','C:\\installers\\nodejs.zip')\"", 300)
    d = wait(tid, timeout=300)
    print(f"  exit={d.get('exit_code') if d else 'timeout'}")
else:
    print("  timeout")
    sys.exit(1)

# Step 4: Verify ZIP size on Windows
print("=== Step 4: Verify downloaded file ===")
tid = submit("dir C:\\installers\\nodejs.zip", 30)
d = wait(tid)
stdout = d.get('stdout','')
print(f"  {stdout.strip()[:200]}")

# Step 5: Run install.ps1 (extract ZIP + install OpenClaw)
print("=== Step 5: Install Node.js + OpenClaw ===")
tid = submit("powershell -ExecutionPolicy Bypass -File C:\\installers\\install.ps1", 300)
d = wait(tid, timeout=300)
if d:
    print(f"  exit={d.get('exit_code')}")
    for line in d.get("stdout","").split("\n"):
        if line.strip():
            print(f"    {line.strip()}")
    if d.get("stderr"):
        for line in d.get("stderr","").split("\n")[:10]:
            print(f"    ! {line.strip()}")
else:
    print("  timeout")
    sys.exit(1)

# Step 6: Final verify
print("=== Step 6: Verify ===")
tid = submit('dir "C:\\Program Files\\nodejs\\" /b & "C:\\Program Files\\nodejs\\node.exe" --version & "C:\\Program Files\\nodejs\\npm.cmd" --version', 30)
d = wait(tid)
if d:
    print(f"  exit={d.get('exit_code')}")
    print(f"  {d.get('stdout','')}")

print("\n=== INSTALLATION COMPLETE ===")