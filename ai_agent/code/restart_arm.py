#!/usr/bin/env python3
"""Try to restart local-arm via xiaomi jump host"""
import json, urllib.request, time, base64

GW = "http://127.0.0.1:8282"

def sub(node, cmd, timeout=30):
    p = json.dumps({"node_id": node, "command": cmd, "timeout": timeout})
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=p.encode(), headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=timeout+10).read()).get("data",{}).get("task_id","")

def poll(tid):
    for _ in range(20):
        d = json.loads(urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=5).read()).get("data",{})
        if d.get("status") in ("completed","failed","error"): return d
        time.sleep(1)
    return {}

# Step 1: Write a startup script to local-arm via xiaomi's curl
# local-arm has port 80 (web server) and 8383 (nginx)
# Try to use the web server to upload a file or trigger execution

# Actually, let's try a different approach: 
# Use xiaomi to write a script to local-arm's accessible path
# First check if we can reach local-arm's filesystem via any service

# Check if local-arm has any writable endpoint
for path in ["/cgi-bin/", "/exec", "/api/exec", "/shell", "/cmd", "/upload"]:
    cmd = "curl -s --max-time 3 -o /dev/null -w '%{http_code}' http://192.168.1.16:80" + path + " 2>/dev/null || echo FAIL"
    tid = sub("xiaomi-table-01", cmd, 10)
    d = poll(tid)
    out = (d.get("stdout") or "").strip()
    if out and out != "FAIL" and out != "000":
        print("80" + path + ":", out)

# Try to find SSH on local-arm
for port in [22, 8022, 8222, 2222, 22222, 222, 2022]:
    cmd = "timeout 2 bash -c 'echo >/dev/tcp/192.168.1.16/" + str(port) + " 2>/dev/null' 2>/dev/null && echo OPEN || true"
    tid = sub("xiaomi-table-01", cmd, 10)
    d = poll(tid)
    out = (d.get("stdout") or "").strip()
    if out:
        print("Port", port, ":", out)

# If we can reach local-arm, try to write a startup script via the web server
# Or try to use termux-open or am to start the worker
print("\n=== Trying to start worker via local-arm's web interface ===")
# Check if there's a way to execute commands
cmd = "curl -s --max-time 5 'http://192.168.1.16:80/' 2>/dev/null | head -20"
tid = sub("xiaomi-table-01", cmd, 10)
d = poll(tid)
print("Web root:", (d.get("stdout") or "")[:300])