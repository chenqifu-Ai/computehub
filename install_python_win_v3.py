#!/usr/bin/env python3
"""安装 Python 到 Windows 节点 - 用 certutil 下载（已验证可靠）"""
import json, urllib.request

nodes = ["wanlida-opc01", "wanlida-opc01-new", "xingke-work01"]

# certutil -urlcache 是之前验证过的可靠下载方式
# 用 cmd 执行，避免 PowerShell 的 URL 解析问题
cmd = (
    'certutil -urlcache -f '
    'http://36.250.122.43:8282/api/v1/download?file=python-embed.zip '
    'C:\\temp\\py_install.zip >nul 2>&1 & '
    'if exist C:\\temp\\py_install.zip ('
    'echo 下载成功 & '
    'powershell -Command "& {Expand-Archive -Path \'C:\\temp\\py_install.zip\' -DestinationPath \'C:\\python311\' -Force}" & '
    'setx PATH "%PATH%;C:\\python311" /M >nul 2>&1 & '
    'python --version 2>&1 & '
    'del /Q C:\\temp\\py_install.zip 2>nul & '
    'echo Python安装完成'
    ') else ('
    'echo 下载失败'
    ')'
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
