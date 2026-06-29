#!/usr/bin/env python3
"""检查升级回滚后状态"""
import base64, json, urllib.request, time

GW = "http://36.250.122.43:8282"
NODE = "windows-home-01"

def ps(cmd):
    b64 = base64.b64encode(cmd.encode("utf-16le")).decode()
    return f"powershell -EncodedCommand {b64}"

def submit(cmd, timeout=10):
    body = {"command": cmd, "timeout": timeout, "priority": 10, "source_type": "direct", "assigned_node": NODE}
    req = urllib.request.Request(GW + "/api/v1/tasks/submit",
        data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read())
    return resp.get("data",{}).get("task_id","")

def poll(tid, max_wait=15):
    for i in range(max_wait):
        time.sleep(1)
        resp = json.loads(urllib.request.urlopen(GW + "/api/v1/tasks/detail?task_id=" + tid, timeout=10).read())
        d = resp.get("data", {})
        if d.get("status") in ("completed", "failed"):
            return d
    return None

print("=== nodes/list ===")
r = json.loads(urllib.request.urlopen(GW + "/api/v1/nodes/list").read())
for n in r["data"]:
    if "windows" in n["node_id"].lower():
        print("  {}: {} v{}".format(n["node_id"], n["status"], n.get("version","?")))

print()
print("=== D:\\\\computehub 文件列表 ===")
tid = submit("cmd /c dir D:\\computehub /b")
d = poll(tid, 12)
if d:
    print(d.get("stdout",""))

print()
print("=== 备份文件检查 ===")
tid = submit("cmd /c if exist D:\\computehub\\computehub.old.exe (echo BACKUP_EXISTS) else (echo NO_BACKUP)")
d = poll(tid, 10)
if d:
    print(d.get("stdout","").strip())

print()
print("=== Gateway API 状态 ===")
tid = submit("curl -s http://localhost:8282/api/v1/nodes/list")
d = poll(tid, 12)
if d:
    out = d.get("stdout","")
    if "success" in out and "true" in out:
        print("  Gateway API: OK")
    else:
        print("  Gateway API: FAIL - " + out[:100])

print()
print("=== Gallery 测试 ===")
tid = submit('curl -s -o NUL -w "%{http_code}" http://localhost:8282/gallery')
d = poll(tid, 12)
if d:
    print("  Gallery HTTP: " + (d.get("stdout","").strip() or "none"))

print()
print("=== AI 页面测试 ===")
tid = submit('curl -s -o NUL -w "%{http_code}" http://localhost:8282/ai')
d = poll(tid, 12)
if d:
    print("  AI HTTP: " + (d.get("stdout","").strip() or "none"))

print()
print("=== Worker health ===")
tid = submit("curl -s http://localhost:8383/api/v1/worker/health")
d = poll(tid, 12)
if d:
    print("  Worker: " + (d.get("stdout","").strip()[:100] or "none"))