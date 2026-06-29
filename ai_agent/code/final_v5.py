#!/usr/bin/env python3
"""Final step: copy new binary + delayed restart"""
import json, urllib.request, time, base64

GW = "http://127.0.0.1:8282"

def sub(node, cmd, timeout=30):
    p = json.dumps({"node_id": node, "command": cmd, "timeout": timeout})
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=p.encode(), headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=timeout+10).read())

def poll(tid):
    for _ in range(30):
        d = json.loads(urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=5).read()).get("data",{})
        if d.get("status") in ("completed","failed","error"): return d
        time.sleep(1)
    return {}

for node, home in [("local-arm","/data/data/com.termux/files/home/OPC"), ("xiaomi-table-01","/data/data/com.termux/files/home/ComputeHub")]:
    print(f"\n=== {node} ===")
    
    # Step 1: Copy binary
    cp = "cp " + home + "/ch-v1.3.17 " + home + "/bin/linux-arm64/computehub && echo COPY_OK"
    tid = sub(node, cp, 30).get("data",{}).get("task_id","")
    d = poll(tid)
    out = (d.get("stdout") or "")[:100]
    print(f"  Copy: {out}")
    
    # Step 2: Queued restart (30 second delay, won't kill the worker mid-task)
    match = node.split("-")[0]
    rscript = "sleep 30;pkill -f 'worker." + match + "' 2>/dev/null;sleep 3;nohup " + home + "/bin/linux-arm64/computehub worker --agent --gw http://36.250.122.43:8282 --node-id " + node + " --interval 3 --concurrent 8 --heartbeat 10 >/dev/null 2>&1 & echo DONE"
    b64 = base64.b64encode(rscript.encode()).decode()
    cmd = "echo " + b64 + " | base64 -d > " + home + "/run_v1.3.17.sh && chmod +x " + home + "/run_v1.3.17.sh && nohup bash " + home + "/run_v1.3.17.sh > /dev/null 2>&1 & echo QUEUED"
    tid = sub(node, cmd, 10).get("data",{}).get("task_id","")
    print(f"  Restart: queued")

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