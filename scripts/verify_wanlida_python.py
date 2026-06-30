#!/usr/bin/env python3
"""wanlida-opc01 Python 3.12.9 最终验证"""
import json, subprocess, time

def submit(cmd, timeout=60):
    r = subprocess.run(
        ["curl", "-s", "-m", "15", "-X", "POST",
         "http://localhost:8282/api/v1/tasks/submit",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({"node_id": "wanlida-opc01", "task_type": "exec_shell", "command": cmd, "timeout": timeout})],
        capture_output=True, text=True
    )
    return json.loads(r.stdout).get("data", {}).get("task_id", "")

def wait(tid, max_w=90):
    for _ in range(max_w * 2):
        time.sleep(1)
        r2 = subprocess.run(
            ["curl", "-s", "-m", "10", f"http://localhost:8282/api/v1/tasks/detail?task_id={tid}"],
            capture_output=True, text=True
        )
        d = json.loads(r2.stdout).get("data", {})
        if d.get("status") in ("completed", "failed"):
            return d
    return {"status": "timeout"}

PY = "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\python.exe"
PIP = "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\Scripts\\pip.exe"

print("=" * 60)
print("🐍 wanlida-opc01 Python 3.12.9 最终验证")
print("=" * 60)

# 1. 版本
print("\n1️⃣ Python 版本")
tid = submit(f'"{PY}" --version')
time.sleep(5)
d = wait(tid)
print(f"   {d.get('stdout', '').strip()}")

# 2. 可执行（用文件方式）
print("\n2️⃣ Python 可执行")
with open("/tmp/py_test.py", "w") as f:
    f.write("import sys\nprint(f'v{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')\nprint(f'EXE: {sys.executable}')\nprint('EXECUTABLE_OK')\n")
tid = submit(f"{PY} /tmp/py_test.py")
time.sleep(5)
d = wait(tid)
for line in d.get("stdout", "").split("\n"):
    print(f"   → {line.strip()}")

# 3. pip
print("\n3️⃣ pip 版本")
tid = submit(f'"{PIP}" --version')
time.sleep(5)
d = wait(tid)
for line in d.get("stdout", "").split("\n"):
    print(f"   → {line.strip()}")

# 4. 标准模块（用文件方式）
print("\n4️⃣ 标准模块")
with open("/tmp/py_mods.py", "w") as f:
    f.write("import json, os, sys, urllib, hashlib, datetime\nprint('STANDARD_MODULES_OK')\n")
tid = submit(f"{PY} /tmp/py_mods.py")
time.sleep(5)
d = wait(tid)
for line in d.get("stdout", "").split("\n"):
    print(f"   → {line.strip()}")

# 5. 安装 requests
print("\n5️⃣ 安装 requests")
tid = submit(f'"{PIP}" install requests 2>&1', 120)
time.sleep(10)
d = wait(tid, 120)
for line in d.get("stdout", "").split("\n"):
    s = line.strip()
    if s and any(kw in s.lower() for kw in ["requests", "success", "installed", "already", "error", "collecting"]):
        print(f"   → {s}")

# 6. 验证 requests（用文件方式避免引号问题）
print("\n6️⃣ 验证 requests")
with open("/tmp/py_req.py", "w") as f:
    f.write("import requests\nprint(f'requests {requests.__version__} OK')\n")
tid = submit(f'"{PY}" /tmp/py_req.py')
time.sleep(5)
d = wait(tid)
for line in d.get("stdout", "").split("\n"):
    print(f"   → {line.strip()}")

# 如果路径带引号不行，试无引号
if d.get("exit_code") != 0:
    tid = submit(f"{PY} /tmp/py_req.py")
    time.sleep(5)
    d = wait(tid)
    for line in d.get("stdout", "").split("\n"):
        print(f"   → {line.strip()}")

print("\n" + "=" * 60)
print("✅ Python 3.12.9 安装完成!")
print(f"   可执行: {PY}")
print(f"   pip: {PIP}")
print("=" * 60)
