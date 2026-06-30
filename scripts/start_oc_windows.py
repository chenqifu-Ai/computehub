"""Start OpenClaw Gateway on windows-mobile via ComputeHub API"""
import json, urllib.request, time, sys

GW = "http://36.250.122.43:8282"
NODE = "windows-mobile"
OC_CMD = "C:\\ProgramData\\nodejs\\node-v24.16.0-win-x64\\openclaw.cmd"

def submit(cmd, timeout=60, node=NODE):
    body = {"node_id": node, "type": "exec", "command": cmd}
    req = urllib.request.Request(
        GW + "/api/v1/tasks/submit",
        data=json.dumps(body).encode(),
        headers={"Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return resp.get("data", {}).get("task_id", "")

def wait(tid, timeout=30):
    for _ in range(timeout):
        time.sleep(1)
        resp = json.loads(urllib.request.urlopen(f"{GW}/api/v1/tasks/detail?task_id={tid}", timeout=10).read())
        d = resp.get("data", {})
        if d.get("status") == "completed":
            return d
    return {"status": "timeout"}

def run(cmd, timeout=60, label=""):
    tid = submit(cmd, timeout)
    d = wait(tid, timeout + 10)
    print(f"  [{label}] exit={d.get('exit_code','?')} | {d.get('stdout','')[:200]}")
    return d

# Step 1: Kill any existing OC gateway
print("[1/3] Kill existing OpenClaw...")
run('taskkill /f /im node.exe 2>nul & taskkill /f /im openclaw* 2>nul', 10)

# Step 2: Start OpenClaw Gateway using Python subprocess (reliable)
print("[2/3] Starting OpenClaw Gateway...")
cmd = f'python -c "import subprocess,time; p=subprocess.Popen([\'{OC_CMD}\',\'gateway\'],stdout=open(\'C:/temp/oc-gw.log\',\'w\'),stderr=subprocess.STDOUT,creationflags=subprocess.CREATE_NEW_PROCESS_GROUP); time.sleep(10); print(\'PID=\'+str(p.pid))"'
d = run(cmd, 30)

# Step 3: Verify
print("[3/3] Verify Gateway...")
d = run("netstat -ano | findstr 18789", 10, "port")
d = run("type C:\\temp\\oc-gw.log 2>nul", 10, "log")