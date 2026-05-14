#!/usr/bin/env python3
"""Windows 节点单独测试"""
import json, time, base64, urllib.request

GW = "http://192.168.1.12:8282"

# 方法1: 直接 Python -c
print("方法1: python -c")
tid = urllib.request.urlopen(urllib.request.Request(
    f"{GW}/api/v1/tasks/submit",
    data=json.dumps({"command": "python -c 'print(123)'", "node_id": "worker-DESKTOP-BUAUIFL"}).encode(),
    headers={"Content-Type": "application/json"}
)).read()
tid = json.loads(tid)["data"]["task_id"]
for _ in range(10):
    time.sleep(2)
    try:
        d = json.loads(urllib.request.urlopen(f"{GW}/api/v1/tasks/detail?task_id={tid}").read())
        if d["data"]["status"] in ("completed", "failed"):
            print(f"  stdout: [{d['data'].get('stdout', '')}]")
            print(f"  stderr: [{d['data'].get('stderr', '')[:100]}]")
            break
    except:
        pass

# 方法2: 用 base64 编码
print("\n方法2: base64 编码")
ps_script = 'Write-Host "HELLO_FROM_WINDOWS"'
b64 = base64.b64encode(ps_script.encode('utf-16-le')).decode('ascii')
full_cmd = f"powershell -EncodedCommand {b64}"
outer_b64 = base64.b64encode(full_cmd.encode('utf-16-le')).decode('ascii')
cmd = f"cmd /c powershell -EncodedCommand {outer_b64}"

tid = urllib.request.urlopen(urllib.request.Request(
    f"{GW}/api/v1/tasks/submit",
    data=json.dumps({"command": cmd, "node_id": "worker-DESKTOP-BUAUIFL"}).encode(),
    headers={"Content-Type": "application/json"}
)).read()
tid = json.loads(tid)["data"]["task_id"]
for _ in range(10):
    time.sleep(2)
    try:
        d = json.loads(urllib.request.urlopen(f"{GW}/api/v1/tasks/detail?task_id={tid}").read())
        if d["data"]["status"] in ("completed", "failed"):
            print(f"  stdout: [{d['data'].get('stdout', '')}]")
            print(f"  stderr: [{d['data'].get('stderr', '')[:100]}]")
            break
    except:
        pass
