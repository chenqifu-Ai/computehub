#!/usr/bin/env python3
"""Setup + Start OpenClaw Gateway on windows-mobile"""
import json, urllib.request, time

GW = "http://localhost:8282"
NODE = "windows-mobile"
OC_DIR = "C:\\ProgramData\\nodejs\\node-v24.16.0-win-x64"

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
    print(f"  [{label}] exit={d.get('exit_code','?')} | {out[:300]}")
    return d

# Step 1: Kill old processes
print("[1/5] Kill old processes...")
run(f'taskkill /f /im node.exe 2>nul', 10, "kill")

# Step 2: Python setup - write config, then start gateway
print("[2/5] Run openclaw setup + start gateway via Python...")

SCRIPT = f'''
import subprocess, time, os

oc_cmd = r"{OC_DIR}\\openclaw.cmd"
cfg_dir = os.path.expanduser("~\\openclaw")
os.makedirs(cfg_dir + "\\config", exist_ok=True)

# Write config with a token
cfg = {{"agents":{{"defaults":{{"model":{{"primary":"ollama-cloud/deepseek-v4-flash"}}}}}},"gateway":{{"port":18789,"token":"setup-token-123"}}}}
import json
with open(cfg_dir + "\\config\\openclaw.json", "w") as f:
    json.dump(cfg, f, indent=2)

# Start gateway
p = subprocess.Popen([oc_cmd, "gateway"],
    stdout=open(r"C:\\temp\\oc-gw.log", "w"),
    stderr=subprocess.STDOUT,
    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
print(f"PID={{p.pid}}", flush=True)

time.sleep(8)
r = subprocess.run("netstat -ano | findstr 18789", shell=True, capture_output=True, text=True)
if r.stdout.strip():
    print("GW_OK:", r.stdout.strip()[:100], flush=True)
else:
    print("GW_FAIL", flush=True)
    with open(r"C:\\temp\\oc-gw.log") as f:
        print(f.read()[-500:], flush=True)
'''

# Encode to base64 to avoid JSON escaping hell
import base64
encoded = base64.b64encode(SCRIPT.encode()).decode()

CMD = f'python -c "import base64; exec(base64.b64decode(\\\"{encoded}\\\").decode())"'
run(CMD, 60, "setup+start")

# Step 3: Verify
print("[3/5] Verify...")
run("netstat -ano | findstr 18789", 10, "port")
run(f"{OC_DIR}\\openclaw.cmd --version", 15, "version")