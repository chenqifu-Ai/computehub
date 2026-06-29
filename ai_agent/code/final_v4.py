#!/usr/bin/env python3
"""Upgrade ARM nodes - download to HOME, not /tmp"""
import json, urllib.request, time, base64

GW = "http://127.0.0.1:8282"
DL = "http://36.250.122.43:8282/api/v1/download?file=computehub-linux-arm64.exe"

def sub(node, cmd, timeout=60):
    p = json.dumps({"node_id": node, "command": cmd, "timeout": timeout})
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=p.encode(), headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=timeout+10).read()).get("data",{}).get("task_id","")

def poll(tid):
    for _ in range(60):
        d = json.loads(urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=5).read()).get("data",{})
        if d.get("status") in ("completed","failed","error"): return d
        time.sleep(1)
    return {}

nodes = [
    ("local-arm", "/data/data/com.termux/files/home/OPC"),
    ("xiaomi-table-01", "/data/data/com.termux/files/home/ComputeHub"),
]

for node, home in nodes:
    print(f"\n=== {node} ===")
    binpath = home + "/bin/linux-arm64/computehub"
    dlpath = home + "/ch-v1.3.17"
    
    dl_cmd = "curl -sL --max-time 120 -o " + dlpath + " " + DL + " 2>&1 && chmod +x " + dlpath + " && echo DL_OK $(wc -c < " + dlpath + ")bytes"
    tid = sub(node, dl_cmd, 120)
    d = poll(tid)
    out = (d.get("stdout") or "")[:100]
    print(f"  DL: {out}")
    if "DL_OK" not in out:
        print(f"  ❌")
        continue
    
    match = node.split("-")[0]
    script = "sleep 45;cp " + dlpath + " " + binpath + ";pkill -f 'worker." + match + "' 2>/dev/null;sleep 3;nohup " + binpath + " worker --agent --gw http://36.250.122.43:8282 --node-id " + node + " --interval 3 --concurrent 8 --heartbeat 10 >/dev/null 2>&1 & echo DONE"
    b64 = base64.b64encode(script.encode()).decode()
    cmd = "echo " + b64 + " | base64 -d > " + home + "/restart.sh && chmod +x " + home + "/restart.sh && nohup bash " + home + "/restart.sh > /dev/null 2>&1 & echo QUEUED"
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