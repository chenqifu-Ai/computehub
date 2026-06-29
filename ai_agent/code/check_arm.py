#!/usr/bin/env python3
"""Check local-arm services from xiaomi"""
import json, urllib.request, time

GW = "http://127.0.0.1:8282"

def sub(node, cmd, timeout=15):
    p = json.dumps({"node_id": node, "command": cmd, "timeout": timeout})
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=p.encode(), headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=timeout+10).read()).get("data",{}).get("task_id","")

def poll(tid):
    for _ in range(15):
        d = json.loads(urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=5).read()).get("data",{})
        if d.get("status") in ("completed","failed","error"): return d
        time.sleep(1)
    return {}

for port, path in [("8383","/api/v1/worker/health"), ("8080","/"), ("80","/")]:
    cmd = "curl -s --max-time 5 http://192.168.1.16:" + port + path + " 2>/dev/null | head -3 || echo FAIL"
    tid = sub("xiaomi-table-01", cmd, 10)
    d = poll(tid)
    out = (d.get("stdout") or "")[:100]
    print(port + ":", out)