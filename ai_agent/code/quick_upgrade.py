#!/usr/bin/env python3
"""Download to temp, queue restart script, done."""
import json, urllib.request, time, base64

GW = "http://127.0.0.1:8282"
DL = "http://36.250.122.43:8282/api/v1/download?file=computehub-linux-arm64.exe"

def sub(node, cmd, timeout=60):
    p = json.dumps({"node_id": node, "command": cmd, "timeout": timeout})
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=p.encode(), headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=timeout+10).read()).get("data",{}).get("task_id","")

def poll(tid):
    for _ in range(60):
        try:
            d = json.loads(urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=5).read()).get("data", {})
            if d.get("status") in ("completed","failed","error"): return d
        except: pass
        time.sleep(1)
    return {}

# Step 1: Download to /tmp
for node in ["local-arm", "xiaomi-table-01"]:
    print(f"\n=== {node} ===")
    dl = "curl -sL --max-time 120 -o /tmp/ch-v1.3.17 " + DL + " 2>&1 && chmod +x /tmp/ch-v1.3.17 && echo DL_OK $(wc -c < /tmp/ch-v1.3.17)bytes"
    tid = sub(node, dl, 120)
    d = poll(tid)
    out = (d.get("stdout") or "")[:100]
    print(f"  DL: {out}")
    if "DL_OK" not in out:
        print(f"  ❌ skip")
        continue

    # Step 2: Write restart script (will run AFTER this task returns)
    script = (
        "sleep 45\n"
        'cp /tmp/ch-v1.3.17 ./bin/linux-arm64/computehub\n'
        'pkill -f "worker.*' + node.split("-")[0] + '" 2>/dev/null\n'
        "sleep 3\n"
        "nohup ./bin/linux-arm64/computehub worker --agent --gw http://36.250.122.43:8282 "
        "--node-id " + node + " --interval 3 --concurrent 8 --heartbeat 10 >/dev/null 2>&1 &\n"
        "echo DONE"
    )
    b64 = base64.b64encode(script.encode()).decode()
    cmd = "echo '" + b64 + "' | base64 -d > /tmp/restart.sh && chmod +x /tmp/restart.sh && nohup bash /tmp/restart.sh > /dev/null 2>&1 & echo QUEUED"
    tid = sub(node, cmd, 10)
    print(f"  ✅ Queued restart")

print("\n⏳ 60s...")
time.sleep(65)

print("\n=== Nodes ===")
r = urllib.request.urlopen(GW + "/api/v1/nodes/list", timeout=5)
for n in json.loads(r.read()).get("data", []):
    print(f"  {n['node_id']} v{n.get('version','?')} {n['status']}")

print("\n=== Hall ===")
r = urllib.request.urlopen(GW + "/api/v1/hall/messages?topic=general&limit=30", timeout=5)
for m in json.loads(r.read()).get("data", {}).get("messages", []):
    print(f"  [{m.get('from_name','?')}] {m.get('content','')[:120]}")