#!/usr/bin/env python3
"""Safe upgrade - no pkill suicide, use script file approach"""
import json, urllib.request, time, base64

GW = "http://127.0.0.1:8282"

def sub(node, cmd, timeout=60):
    body = json.dumps({"node_id": node, "command": cmd, "timeout": timeout}).encode()
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=body, headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=timeout+10).read())

def poll(tid, max_wait=60):
    for _ in range(max_wait):
        try:
            d = json.loads(urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=5).read()).get("data", {})
            s = d.get("status", "")
            if s in ("completed","failed","error","cancelled"):
                return d
        except: pass
        time.sleep(1)
    return {}

# Step 1: Write restart script to /tmp on the node (won't kill current worker)
restart_script = """#!/bin/bash
# Restart worker with --agent mode
sleep 3
OLD_PID=$(pgrep -f "worker.*NODEID" | head -1)
kill $OLD_PID 2>/dev/null
sleep 2
cd /BIN_DIR
nohup ./bin/linux-arm64/computehub worker --agent --gw http://36.250.122.43:8282 --node-id NODEID --interval 3 --concurrent 8 --heartbeat 10 >/dev/null 2>&1 &
echo "Worker restarted with --agent, PID=$!"
"""

dl_script = """#!/usr/bin/env python3
import urllib.request, hashlib, os
url = "http://36.250.122.43:8282/api/v1/download?file=computehub-linux-arm64.exe"
d = urllib.request.urlopen(url, timeout=120).read()
h = hashlib.sha256(d).hexdigest()
print("DL_OK", len(d), "bytes SHA256=" + h)
with open("/tmp/ch-v1.3.17", "wb") as f: f.write(d)
os.chmod("/tmp/ch-v1.3.17", 0o755)
import subprocess, sys
r = subprocess.run(["cp", "/tmp/ch-v1.3.17", sys.argv[1]], capture_output=True, text=True)
print("COPY:", r.returncode, r.stdout[:50])
"""

ARM_BIN = "./bin/linux-arm64/computehub"
dl_b64 = base64.b64encode(dl_script.encode()).decode()

for node_id, bin_path in [("local-arm", ARM_BIN), ("xiaomi-table-01", ARM_BIN)]:
    print(f"\n=== {node_id} ===")
    
    # Step 1: Download binary via Python script
    cmd = f"echo '{dl_b64}' | base64 -d > /tmp/dl_v1.3.17.py && python3 /tmp/dl_v1.3.17.py {bin_path}"
    r = sub(node_id, cmd, 120)
    tid = r.get("data",{}).get("task_id","")
    d = poll(tid, 90)
    out = (d.get("stdout") or "")
    print(f"  DL: {out[:150]}")
    
    if "DL_OK" in out:
        # Step 2: Write restart script (won't kill self because worker already done)
        rs = restart_script.replace("NODEID", node_id).replace("BIN_DIR", "")
        rs_b64 = base64.b64encode(rs.encode()).decode()
        cmd = f"echo '{rs_b64}' | base64 -d > /tmp/restart_v1.3.17.sh && chmod +x /tmp/restart_v1.3.17.sh && nohup bash /tmp/restart_v1.3.17.sh > /tmp/restart_log.txt 2>&1 & echo RESTART_QUEUED_PID=$!"
        r = sub(node_id, cmd, 10)  # short timeout, just queue the restart
        print(f"  Restart queued")
        time.sleep(2)
    else:
        print(f"  ❌ DL failed")

print("\n⏳ Waiting 20s for workers to restart...")
time.sleep(25)

print("\n=== Nodes ===")
try:
    r = urllib.request.urlopen(GW + "/api/v1/nodes/list", timeout=5)
    for n in json.loads(r.read()).get("data", []):
        print(f"  {n['node_id']} v{n.get('version','?')} {n['status']}")
except: pass

print("\n=== Hall ===")
try:
    r = urllib.request.urlopen(GW + "/api/v1/hall/messages?topic=general&limit=30", timeout=5)
    for m in json.loads(r.read()).get("data", {}).get("messages", []):
        print(f"  [{m.get('from_name','?')}] {m.get('content','')[:120]}")
except: pass