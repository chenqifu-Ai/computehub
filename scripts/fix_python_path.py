#!/usr/bin/env python3
"""Fix PATH and verify Python on wanlida-opc01"""
import json, subprocess, time, base64

def submit(cmd, timeout=30):
    r = subprocess.run(
        ["curl", "-s", "-m", "15", "-X", "POST",
         "http://localhost:8282/api/v1/tasks/submit",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"node_id": "wanlida-opc01", "task_type": "exec_shell", "command": cmd, "timeout": timeout})],
        capture_output=True, text=True
    )
    return json.loads(r.stdout).get("data", {}).get("task_id", "")

def wait(tid):
    for _ in range(30 * 2):
        time.sleep(1)
        r2 = subprocess.run(
            ["curl", "-s", "-m", "10", f"http://localhost:8282/api/v1/tasks/detail?task_id={tid}"],
            capture_output=True, text=True
        )
        d = json.loads(r2.stdout).get("data", {})
        if d.get("status") in ("completed", "failed"):
            return d
    return {"status": "timeout"}

# PowerShell code to set PATH
py_path = r"C:\Users\admin\AppData\Local\Programs\Python\Python312"
py_scripts = r"C:\Users\admin\AppData\Local\Programs\Python\Python312\Scripts"

ps_code = f"""
$py = "{py_path}"
$ps = "{py_scripts}"
$current = [Environment]::GetEnvironmentVariable("Path", "User")
$new = $py + ";" + $ps + ";" + $current
[Environment]::SetEnvironmentVariable("Path", $new, "User")
Write-Host "PATH_UPDATED"
$env:Path = $new
python --version
pip --version
python -c "print('python_works')"
pip install requests -q
python -c "import requests; print('requests_ok:', requests.__version__)"
"""

b64 = base64.b64encode(ps_code.encode('utf-16-le')).decode('ascii')
cmd = f"powershell -EncodedCommand {b64}"
print(f"📤 Submitting: {cmd[:80]}...")

tid = submit(cmd, 120)
time.sleep(5)
d = wait(tid)
print(f"\n✅ 结果: exit={d.get('exit_code')} dur={d.get('duration')}")
stdout = d.get("stdout", "")
stderr = d.get("stderr", "")
for line in stdout.split("\n"):
    if line.strip():
        print(f"   {line.strip()}")
if stderr.strip():
    for line in stderr.split("\n"):
        if line.strip() and "warning" not in line.lower():
            print(f"   ! {line.strip()[:200]}")
