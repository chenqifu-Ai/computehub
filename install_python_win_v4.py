#!/usr/bin/env python3
"""安装 Python 到 Windows 节点 - 纯 PowerShell .NET 方式"""
import json, urllib.request

nodes = ["wanlida-opc01", "wanlida-opc01-new", "xingke-work01"]

# 用 .NET WebClient 下载，URL 用单引号避免解析问题
cmd = (
    "[Net.ServicePointManager]::SecurityProtocol=[Net.SecurityProtocolType]::Tls12; "
    "$wc=New-Object Net.WebClient; "
    "$wc.DownloadFile('http://36.250.122.43:8282/api/v1/download?file=python-embed.zip','C:\\temp\\py_install.zip'); "
    "if(Test-Path 'C:\\temp\\py_install.zip'){"
    "  Write-Output '下载成功'; "
    "  Expand-Archive 'C:\\temp\\py_install.zip' 'C:\\python311' -Force; "
    "  $p=[Environment]::GetEnvironmentVariable('Path','Machine'); "
    "  if($p -notlike '*C:\\python311*'){[Environment]::SetEnvironmentVariable('Path',\"$p;C:\\python311\",'Machine')}; "
    "  $env:Path+=';C:\\python311'; "
    "  python --version 2>&1; "
    "  Remove-Item 'C:\\temp\\py_install.zip' -Force -ErrorAction SilentlyContinue; "
    "  Write-Output 'Python安装完成'"
    "}else{"
    "  Write-Output '下载失败'"
    "}"
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
