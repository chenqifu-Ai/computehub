#!/usr/bin/env python3
"""提交 Python 安装任务到 Windows 节点"""
import json, urllib.request, sys

nodes = ["wanlida-opc01", "wanlida-opc01-new", "xingke-work01"]

cmd = (
    "$wc=New-Object Net.WebClient; "
    "$wc.DownloadFile('http://36.250.122.43:8282/api/v1/download?file=python-embed.zip','C:\\temp\\py.zip'); "
    "if(!(Test-Path 'C:\\python311')){New-Item -ItemType Directory 'C:\\python311' -Force|Out-Null}; "
    "Expand-Archive 'C:\\temp\\py.zip' 'C:\\python311' -Force; "
    "$p=[Environment]::GetEnvironmentVariable('Path','Machine'); "
    "if($p -notlike '*C:\\python311*'){[Environment]::SetEnvironmentVariable('Path',\"$p;C:\\python311\",'Machine')}; "
    "$env:Path+=';C:\\python311'; "
    "python --version 2>&1; "
    "Remove-Item 'C:\\temp\\py.zip' -Force -ErrorAction SilentlyContinue; "
    "Write-Output '✅ Python 安装完成'"
)

for node in nodes:
    payload = json.dumps({
        "command": cmd,
        "node_id": node,
        "name": "安装Python",
        "timeout": 120
    }).encode()
    
    req = urllib.request.Request(
        "http://36.250.122.43:8282/api/v1/tasks/submit",
        data=payload,
        headers={"Content-Type": "application/json"}
    )
    resp = json.loads(urllib.request.urlopen(req).read())
    tid = resp.get("data", {}).get("task_id", "?")
    print(f"📤 {node} → {tid}")
