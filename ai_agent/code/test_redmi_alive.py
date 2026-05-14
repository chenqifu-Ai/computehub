#!/usr/bin/env python3
import json, time, urllib.request
GW = "http://192.168.1.12:8282"
req = urllib.request.Request(f"{GW}/api/v1/tasks/submit", data=json.dumps({"command": "echo REDMI_ALIVE", "node_id": "redmi-1"}).encode(), headers={"Content-Type": "application/json"})
resp = urllib.request.urlopen(req, timeout=10)
task_id = json.loads(resp.read())["data"]["task_id"]
for i in range(20):
    time.sleep(2)
    try:
        resp = urllib.request.urlopen(urllib.request.Request(f"{GW}/api/v1/tasks/detail?task_id={task_id}"), timeout=10)
        detail = json.loads(resp.read())
        if detail["data"]["status"] in ("completed", "failed"):
            print(f"Status: {detail['data']['status']}")
            print(f"Exit: {detail['data'].get('exit_code')}")
            print(f"Stdout: {detail['data'].get('stdout', '')}")
            print(f"Stderr: {detail['data'].get('stderr', '')}")
            break
    except Exception as e:
        print(f"Check failed: {e}")
