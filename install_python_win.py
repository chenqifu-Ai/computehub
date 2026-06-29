#!/usr/bin/env python3
"""安装 Python 到 Windows 节点 - 用 curl.exe 下载"""
import json, urllib.request

nodes = ["wanlida-opc01", "wanlida-opc01-new", "xingke-work01"]

# 用 curl.exe (Windows 10+ 自带) 下载，避免 PowerShell URL 解析问题
cmd = (
    'Remove-Item "C:\\temp\\py_install.zip" -Force -ErrorAction SilentlyContinue; '
    'Remove-Item "C:\\python311" -Recurse -Force -ErrorAction SilentlyContinue; '
    'New-Item -ItemType Directory "C:\\python311" -Force | Out-Null; '
    'curl.exe -sL "http://36.250.122.43:8282/api/v1/download?file=python-embed.zip" -o "C:\\temp\\py_install.zip"; '
    'Expand-Archive "C:\\temp\\py_install.zip" "C:\\python311" -Force; '
    '$p=[Environment]::GetEnvironmentVariable("Path","Machine"); '
    'if($p -notlike "*C:\\python311*"){[Environment]::SetEnvironmentVariable("Path","$p;C:\\python311","Machine")}; '
    '$env:Path+=";C:\\python311"; '
    'python --version 2>&1; '
    'Remove-Item "C:\\temp\\py_install.zip" -Force -ErrorAction SilentlyContinue; '
    'Write-Output "Python 安装完成"'
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
