#!/usr/bin/env python3
"""Scan local-arm ports from xiaomi-table-01"""
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

for port in [22, 8022, 8222, 2222, 8021, 8023, 8383, 8282, 8080, 3000, 9090, 443, 80]:
    cmd = "timeout 2 bash -c 'echo >/dev/tcp/192.168.1.16/" + str(port) + " 2>/dev/null' 2>/dev/null && echo PORT_" + str(port) + "_OPEN || true"
    tid = sub("xiaomi-table-01", cmd, 10)
    if tid:
        d = poll(tid)
        out = (d.get("stdout") or "").strip()
        if out:
            print(out)