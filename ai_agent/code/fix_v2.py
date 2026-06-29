#!/usr/bin/env python3
"""Final fix: push DL script via base64, then exec"""
import json, urllib.request, time, base64, sys

GW = "http://127.0.0.1:8282"

def sub(node, cmd, timeout=120):
    p = json.dumps({"node_id": node, "command": cmd, "timeout": timeout}).encode()
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=p, headers={"Content-Type":"application/json"})
    resp = urllib.request.urlopen(r, timeout=timeout+10)
    return json.loads(resp.read())

def poll(tid, max_wait=120):
    for _ in range(max_wait):
        try:
            r = urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=5)
            d = json.loads(r.read()).get("data", {})
            s = d.get("status", "")
            if s in ("completed","failed","error","cancelled"):
                return d
        except:
            pass
        time.sleep(1)
    return {"error":"timeout"}

# Download script
dl_script = """import urllib.request, hashlib, os
url = "http://36.250.122.43:8282/api/v1/download?file=computehub-linux-arm64.exe"
d = urllib.request.urlopen(url, timeout=120).read()
h = hashlib.sha256(d).hexdigest()
print("GOT", len(d), h)
with open("/tmp/ch-v1.3.17", "wb") as f: f.write(d)
os.chmod("/tmp/ch-v1.3.17", 0o755)
print("OK")
"""
dl_b64 = base64.b64encode(dl_script.encode()).decode()

arm_bin = "/root/bin/linux-arm64/computehub"

for node in ["local-arm", "xiaomi-table-01"]:
    print(f"=== {node} ===")
    cmd = "echo '" + dl_b64 + "' | base64 -d > /tmp/dl.py && python3 /tmp/dl.py"
    r = sub(node, cmd, 120)
    tid = r.get("data", {}).get("task_id", "")
    if not tid:
        print(f"  Submit fail: {r}")
        continue
    d = poll(tid, 90)
    out = (d.get("stdout") or "")[:200]
    err = (d.get("stderr") or "")[:100]
    print(f"  {out}")
    if err and "error" not in out:
        print(f"  stderr: {err}")
    
    if "OK" in out:
        restart = "cp /tmp/ch-v1.3.17 " + arm_bin + " && pkill -f 'computehub.*" + node.split("-")[0] + "' 2>/dev/null; sleep 2; nohup " + arm_bin + " worker --agent --gw http://36.250.122.43:8282 --node-id " + node + " --interval 3 --concurrent 8 --heartbeat 10 > /dev/null 2>&1 & echo RESTART_OK"
        r = sub(node, restart, 30)
        print(f"  ✅ Upgraded")
    else:
        print(f"  ❌ Failed")

print("\n⏳ 25s...")
time.sleep(25)

print("\n=== Nodes ===")
r = urllib.request.urlopen(GW + "/api/v1/nodes/list", timeout=5)
for n in json.loads(r.read()).get("data", []):
    print(f"  {n.get('node_id','?')} v{n.get('version','?')} {n.get('status','')}")

print("\n=== Hall ===")
try:
    r = urllib.request.urlopen(GW + "/api/v1/hall/messages?topic=general&limit=30", timeout=5)
    for m in json.loads(r.read()).get("data", {}).get("messages", []):
        print(f"  [{m.get('from_name','?')}] {m.get('content','')[:120]}")
except:
    pass