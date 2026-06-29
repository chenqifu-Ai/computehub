#!/usr/bin/env python3
"""Final: restart ARM nodes with correct paths"""
import json, urllib.request, time

GW = "http://127.0.0.1:8282"

def sub(node, cmd, timeout=30):
    body = json.dumps({"node_id": node, "command": cmd, "timeout": timeout}).encode()
    r = urllib.request.Request(GW + "/api/v1/tasks/submit", data=body, headers={"Content-Type":"application/json"})
    return json.loads(urllib.request.urlopen(r, timeout=timeout+10).read())

def poll(tid, max_wait=30):
    for _ in range(max_wait):
        try:
            d = json.loads(urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=5).read()).get("data", {})
            s = d.get("status", "")
            if s in ("completed","failed","error","cancelled"):
                return d
        except:
            pass
        time.sleep(1)
    return {}

# Restart local-arm with new binary
print("=== local-arm restart ===")
cmd = 'pkill -f "worker.*local-arm" 2>/dev/null; pkill -f "computehub.*local-arm" 2>/dev/null; sleep 3; nohup ./bin/linux-arm64/computehub worker --agent --gw http://36.250.122.43:8282 --node-id local-arm --interval 3 --concurrent 8 --heartbeat 10 >/dev/null 2>&1 & echo RESTART_OK'
r = sub("local-arm", cmd, 30)
print("sent:", r.get("data",{}).get("task_id","?")[:30])

# Check xiaomi download task
print("=== xiaomi status ===")
d = poll("task-1780705773505-1dd695", 90)
out = d.get("stdout", "")[:200]
print("xiaomi DL:", out)

# If xiaomi done, kill+restart
if out:
    # Already downloaded, just need to restart with --agent
    cmd2 = 'pkill -f "worker.*xiaomi-table" 2>/dev/null; sleep 3; nohup ./bin/linux-arm64/computehub worker --agent --gw http://36.250.122.43:8282 --node-id xiaomi-table-01 --interval 3 --concurrent 8 --heartbeat 10 >/dev/null 2>&1 & echo RESTART_OK'
    r2 = sub("xiaomi-table-01", cmd2, 30)
    print("xiaomi restart sent:", r2.get("data",{}).get("task_id","?")[:30])

print("Waiting 30s...")
time.sleep(30)

print("\n=== Nodes ===")
r = urllib.request.urlopen(GW + "/api/v1/nodes/list", timeout=5)
for n in json.loads(r.read()).get("data", []):
    print(f"  {n['node_id']} v{n.get('version','?')} {n['status']}")

print("\n=== Hall ===")
try:
    r = urllib.request.urlopen(GW + "/api/v1/hall/messages?topic=general&limit=30", timeout=5)
    for m in json.loads(r.read()).get("data", {}).get("messages", []):
        print(f"  [{m.get('from_name','?')}] {m.get('content','')[:100]}")
except: pass