#!/usr/bin/env python3
"""Delayed restart upgrade - never kill worker mid-task"""
import json, urllib.request, time

GW = "http://127.0.0.1:8282"

def sub(node, cmd, timeout=60):
    p = json.dumps({"node_id": node, "command": cmd, "timeout": timeout})
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=p.encode(), headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=timeout+10).read()).get("data",{}).get("task_id","")

def poll(tid):
    for _ in range(60):
        try:
            d = json.loads(urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=5).read()).get("data", {})
            s = d.get("status", "")
            if s in ("completed","failed","error"): return d
        except: pass
        time.sleep(1)
    return {}

BIN = "./bin/linux-arm64/computehub"
GW_URL = "http://36.250.122.43:8282"
DL_URL = "http://36.250.122.43:8282/api/v1/download?file=computehub-linux-arm64.exe"

for node in ["local-arm", "xiaomi-table-01"]:
    print(f"\n=== {node} ===")
    match_str = node.split("-")[0]
    
    # Step 1: curl download (works reliably)
    dl_cmd = "curl -sL --max-time 120 -o " + BIN + " " + DL_URL + " 2>&1 && chmod +x " + BIN + " && echo DL_OK $(wc -c < " + BIN + ")bytes"
    tid = sub(node, dl_cmd, 120)
    d = poll(tid)
    out = (d.get("stdout") or "")[:120]
    print(f"  DL: {out}")
    
    if "DL_OK" not in out:
        err = (d.get("stderr") or "")[:100]
        print(f"  ❌ DL failed: {err if err else 'unknown'}")
        continue
    
    # Step 2: Write restart script to /tmp (will kill old worker AFTER returning)
    restart_script = (
        "#!/bin/bash\n"
        "sleep 60\n"
        'OLD=$(pgrep -f "worker.*' + match_str + '" | head -1)\n'
        "kill $OLD 2>/dev/null\n"
        "sleep 3\n"
        "nohup " + BIN + " worker --agent --gw " + GW_URL + " --node-id " + node + " --interval 3 --concurrent 8 --heartbeat 10 >/dev/null 2>&1 &\n"
        "echo FINALLY_RESTARTED_PID=$!\n"
    )
    import base64
    b64 = base64.b64encode(restart_script.encode()).decode()
    
    write_cmd = "echo '" + b64 + "' | base64 -d > /tmp/restart_v1.3.17.sh && chmod +x /tmp/restart_v1.3.17.sh && nohup bash /tmp/restart_v1.3.17.sh > /tmp/restart_log.txt 2>&1 & echo SCHEDULED"
    tid = sub(node, write_cmd, 10)
    print(f"  ✅ Restart scheduled (will execute in ~60s)")
    time.sleep(2)

print("\n⏳ Waiting 80s for delayed restart...")
time.sleep(85)

print("\n=== Nodes ===")
r = urllib.request.urlopen(GW + "/api/v1/nodes/list", timeout=5)
for n in json.loads(r.read()).get("data", []):
    print(f"  {n['node_id']} v{n.get('version','?')} {n['status']}")

print("\n=== Hall ===")
r = urllib.request.urlopen(GW + "/api/v1/hall/messages?topic=general&limit=30", timeout=5)
for m in json.loads(r.read()).get("data", {}).get("messages", []):
    print(f"  [{m.get('from_name','?')}] {m.get('content','')[:120]}")