#!/usr/bin/env python3
"""Download binary to local-arm using proper JSON"""
import json, urllib.request, time

GW = "http://127.0.0.1:8282"

def sub(node, cmd, timeout=120):
    body = json.dumps({"node_id": node, "command": cmd, "timeout": timeout})
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=body.encode(), headers={"Content-Type":"application/json"})
    resp = urllib.request.urlopen(r, timeout=timeout+10)
    return json.loads(resp.read()).get("data",{}).get("task_id","")

def poll(tid):
    for _ in range(90):
        d = json.loads(urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=5).read()).get("data",{})
        if d.get("status") in ("completed","failed","error"): return d
        time.sleep(1)
    return {}

# Python one-liner to download binary
# Using single quotes inside so shell doesn't expand
dl_cmd = (
    "python3 -c 'import urllib.request as u; "
    "d=u.urlopen(\"http://36.250.122.43:8282/api/v1/download?file=computehub-linux-arm64.exe\",timeout=120).read(); "
    "open(\"/data/data/com.termux/files/home/OPC/ch-v1.3.17\",\"wb\").write(d); "
    "import os; os.chmod(\"/data/data/com.termux/files/home/OPC/ch-v1.3.17\",0o755); "
    "print(\"OK\",len(d),\"bytes\")'"
)

print("=== local-arm ===")
tid = sub("local-arm", dl_cmd, 120)
print(f"  Task: {tid[:30]}")
d = poll(tid)
out = (d.get("stdout") or "")[:200]
err = (d.get("stderr") or "")[:200]
print(f"  out: {out}")
if err: print(f"  err: {err}")

if "OK" in out:
    # Copy + delayed restart
    cp_cmd = "cp /data/data/com.termux/files/home/OPC/ch-v1.3.17 /data/data/com.termux/files/home/OPC/bin/linux-arm64/computehub && echo COPY_OK"
    tid = sub("local-arm", cp_cmd, 15)
    poll(tid)
    
    # Queued restart (30s delay)
    rcmd = (
        "nohup bash -c 'sleep 30; "
        "pkill -f \"worker.*local-arm\" 2>/dev/null; sleep 3; "
        "nohup /data/data/com.termux/files/home/OPC/bin/linux-arm64/computehub "
        "worker --agent --gw http://36.250.122.43:8282 --node-id local-arm "
        "--interval 3 --concurrent 8 --heartbeat 10 >/dev/null 2>&1 & echo DONE' "
        "> /dev/null 2>&1 & echo QUEUED"
    )
    tid = sub("local-arm", rcmd, 10)
    print(f"  Restart queued")

print("\n⏳ 45s...")
time.sleep(50)

print("\n=== Nodes ===")
r = urllib.request.urlopen(GW + "/api/v1/nodes/list", timeout=5)
for n in json.loads(r.read()).get("data", []):
    print(f"  {n['node_id']} v{n.get('version','?')} {n['status']}")

print("\n=== Hall ===")
r = urllib.request.urlopen(GW + "/api/v1/hall/messages?topic=general&limit=30", timeout=5)
for m in json.loads(r.read()).get("data", {}).get("messages", []):
    print(f"  [{m.get('from_name','?')}] {m.get('content','')[:120]}")