#!/usr/bin/env python3
"""Windows OpenClaw Gateway setup - run from ECS"""
import json, urllib.request, time

GW = "http://localhost:8282"
NODE = "windows-mobile"

def submit(cmd, timeout=120):
    body = json.dumps({"node_id": NODE, "type": "exec", "command": cmd}).encode()
    req = urllib.request.Request(GW + "/api/v1/tasks/submit", data=body,
        headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return resp.get("data", {}).get("task_id", "")

def wait(tid, max_wait=120):
    for _ in range(max_wait):
        time.sleep(1)
        resp = json.loads(urllib.request.urlopen(f"{GW}/api/v1/tasks/detail?task_id={tid}", timeout=10).read())
        d = resp.get("data", {})
        if d.get("status") == "completed":
            return d
    return {"status": "timeout"}

def run(cmd, timeout=60, label=""):
    tid = submit(cmd, timeout)
    d = wait(tid, timeout + 10)
    out = (d.get("stdout") or "").strip()
    print(f"  [{label}] exit={d.get('exit_code','?')} | dur={d.get('duration','?')} | {out[:200]}")
    return d

# Step 1: Kill old OC processes
print("[1/4] Kill old processes...")
run('taskkill /f /im node.exe 2>nul & taskkill /f /im openclaw* 2>nul', 10, "kill")

# Step 2: Start Gateway with full path, redirect output
print("[2/4] Start OpenClaw Gateway...")
OC_CMD = "C:\\ProgramData\\nodejs\\node-v24.16.0-win-x64\\openclaw.cmd"
run(f'start /min cmd /c ""{OC_CMD}" gateway > C:\\temp\\oc-gw.log 2>&1"', 15, "launch")

# Step 3: Wait and check port
print("[3/4] Wait for port...")
for i in range(12):
    time.sleep(5)
    tid = submit("netstat -ano | findstr 18789", 10)
    d = wait(tid, 15)
    out = (d.get("stdout") or "").strip()
    if out:
        print(f"  [port] Found! {out[:100]}")
        break
    print(f"  [port] Attempt {i+1}/12: not ready yet...")
else:
    print("  [port] FAILED - checking logs...")
    run("type C:\\temp\\oc-gw.log 2>nul", 10, "log")

# Step 4: Verify
print("[4/4] Final check...")
run("tasklist | findstr node", 10, "process")
run("C:\\ProgramData\\nodejs\\node-v24.16.0-win-x64\\openclaw.cmd --version", 15, "version")