#!/usr/bin/env python3
"""检查 Windows 节点 Python 安装情况"""
import json, urllib.request

nodes = ["wanlida-opc01", "wanlida-opc01-new", "xingke-work01"]

for node in nodes:
    payload = json.dumps({
        "command": 'dir C:\\python311 2>&1',
        "node_id": node,
        "name": "检查目录"
    }).encode()
    req = urllib.request.Request(
        "http://36.250.122.43:8282/api/v1/tasks/submit",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    tid = resp.get("data", {}).get("task_id", "?")
    print(f"📤 {node} → {tid}")
