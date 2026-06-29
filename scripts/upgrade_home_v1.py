#!/usr/bin/env python3
"""Upgrade windows-home-01 to v1.3.24"""
import json, urllib.request, time

GW = "http://36.250.122.43:8282"

def submit(node_id, command, timeout=120):
    task = {"node_id": node_id, "command": command, "timeout": timeout, "priority": 10}
    req = urllib.request.Request(
        f"{GW}/api/v1/tasks/submit",
        data=json.dumps(task).encode(),
        headers={"Content-Type": "application/json"}, method="POST"
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def poll(task_id, timeout_s=60):
    for i in range(timeout_s // 3):
        time.sleep(3)
        with urllib.request.urlopen(f"{GW}/api/v1/tasks/detail?task_id={task_id}", timeout=10) as resp:
            d = json.loads(resp.read())
            if d.get("success") and d.get("data"):
                s = d["data"].get("status", "?")
                print(f"  [{i+1}] {s}", flush=True)
                if s in ("completed", "failed"):
                    return d["data"]
    return None

# Phase 1: Download new binary
print("=== Phase 1: Download v1.3.24 binary ===")
dl_cmd = (
    'powershell -Command "& {'
    '$url=\"http://36.250.122.43:8282/api/v1/download?file=computehub-windows-amd64.exe\";'
    '$out=\"D:\\computehub\\computehub.v1.3.24.exe\";'
    '[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12;'
    '$wc=New-Object System.Net.WebClient;'
    '$wc.DownloadFile($url,$out);'
    'Write-Host Downloaded: $out;'
    'if(Test-Path $out){Write-Host OK}'
    '}"'
)
res = submit("windows-home-01", dl_cmd, timeout=120)
tid = res["data"]["task_id"]
print(f"Task: {tid}")
r = poll(tid, 90)
if r:
    print(f"Exit: {r.get('exit_code')}")
    print(f"Stdout: {r.get('stdout','')[:300]}")
    print(f"Stderr: {r.get('stderr','')[:300]}")