#!/usr/bin/env python3
"""安装 Python 到 Windows 节点 - 用 cmd /c curl.exe 避免 PowerShell URL 问题"""
import json, urllib.request

nodes = ["wanlida-opc01", "wanlida-opc01-new", "xingke-work01"]

# 用 cmd /c 执行 curl.exe，完全避开 PowerShell 的 URL 解析
cmd = (
    'cmd /c "curl.exe -sL http://36.250.122.43:8282/api/v1/download?file=python-embed.zip -o C:\\temp\\py_install.zip '
    '&& if exist C:\\temp\\py_install.zip ('
    'echo 下载成功 && '
    'powershell -Command Expand-Archive -Path C:\\temp\\py_install.zip -DestinationPath C:\\python311 -Force && '
    'setx PATH %%PATH%%;C:\\python311 /M >nul && '
    'C:\\python311\\python.exe --version && '
    'del /Q C:\\temp\\py_install.zip && '
    'echo Python安装完成'
    ') else ('
    'echo 下载失败'
    ')"'
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
