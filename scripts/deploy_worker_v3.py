#!/usr/bin/env python3
"""用 PowerShell WriteAllText 上传 Python 脚本到 wanlida-opc01"""
import json, subprocess, time, base64

def submit(cmd, timeout=120):
    r = subprocess.run(
        ["curl", "-s", "-m", "15", "-X", "POST",
         "http://localhost:8282/api/v1/tasks/submit",
         "-H", "Content-Type: application/json",
         "-d", json.dumps({
             "node_id": "wanlida-opc01",
             "task_type": "exec_shell",
             "command": cmd,
             "timeout": timeout
         })],
        capture_output=True, text=True
    )
    return json.loads(r.stdout).get("data", {}).get("task_id", "")

def wait(tid, max_w=120):
    for _ in range(max_w * 2):
        time.sleep(1)
        r2 = subprocess.run(
            ["curl", "-s", "-m", "10",
             f"http://localhost:8282/api/v1/tasks/detail?task_id={tid}"],
            capture_output=True, text=True
        )
        d = json.loads(r2.stdout).get("data", {})
        if d.get("status") in ("completed", "failed"):
            return d
    return {"status": "timeout"}

# 用 WriteAllBytes + Base64 上传
content = b"""import urllib.request
import os
url = 'http://36.250.122.43:8282/api/v1/download?file=computehub.exe&platform=windows-amd64'
dest = 'C:\\installers\\computehub.exe'
urllib.request.urlretrieve(url, dest)
size = os.path.getsize(dest)
print('DOWNLOAD_OK ' + str(size) + ' bytes')
"""

b64 = base64.b64encode(content).decode()

# 方法：用 cmd 直接执行 python -c
# Python 脚本太复杂，换个思路 — 让 Gateway 直接通过 exec_shell 下载
# 用 Python 在远程机器上写文件

# 第一步：上传 Write-File.ps1（一个小的 PowerShell 脚本）
writer_content = b"""
param([string]$Path, [string]$Content)
[System.IO.File]::WriteAllText($Path, $Content, [System.Text.Encoding]::UTF8)
"""
writer_b64 = base64.b64encode(writer_content).decode()

print("📤 上传写文件脚本...")
# 用 echo 创建 .ps1 文件
echo_cmd = """echo param([string]$Path, [string]$Content) > C:\\installers\\w.ps1
echo [System.IO.File]::WriteAllText($Path, $Content, [System.Text.Encoding]::UTF8) >> C:\\installers\\w.ps1
echo WRITER_UPLOADED"""

tid0 = submit(echo_cmd, 30)
time.sleep(5)
d0 = wait(tid0)
print(f"   echo 写 w.ps1: exit={d0.get('exit_code')} stdout={d0.get('stdout','').strip()[:50]}")

# 第二步：通过 Gallery 上传 dl.py（用 Python 脚本）
# 更简单：让 Gateway 通过 download 端点给远程机器传文件
# 但 Worker 下载端点是 /api/v1/download，不是上传

# 最靠谱的方式：curl 到远程 Python 下载
print("\n📥 下载 Worker...")
# 构造远程命令 — 用 python -c 但用短路径
# Python 路径不带引号没问题，因为它不含空格
PY = "C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\python.exe"

# 用 python -c 执行一段简单的代码
# 把 download.py 写到远程
dl_content = b"""import urllib.request as u, os, sys
url = sys.argv[1] if len(sys.argv) > 1 else 'http://36.250.122.43:8282/api/v1/download?file=computehub.exe&platform=windows-amd64'
dest = sys.argv[2] if len(sys.argv) > 2 else 'C:\\installers\\computehub.exe'
u.urlretrieve(url, dest)
print('OK ' + str(os.path.getsize(dest)))
"""

# 先写 dl.py
write_dl = 'echo import urllib.request as u, os, sys > C:\\installers\\dl.py && echo url = sys.argv[1] if len(sys.argv) > 1 else \'http://36.250.122.43:8282/api/v1/download?file=computehub.exe&platform=windows-amd64\' >> C:\\installers\\dl.py && echo dest = sys.argv[2] if len(sys.argv) > 2 else \'C:\\installers\\computehub.exe\' >> C:\\installers\\dl.py && echo u.urlretrieve(url, dest) >> C:\\installers\\dl.py && echo print(\'OK \' + str(os.path.getsize(dest))) >> C:\\installers\\dl.py && echo WRITTEN'

tid1 = submit(write_dl, 30)
time.sleep(5)
d1 = wait(tid1)
print(f"   写 dl.py: exit={d1.get('exit_code')} stdout={d1.get('stdout','').strip()[:50]}")

# 执行 dl.py
print("\n📥 执行下载...")
# 用 python 执行 dl.py 但传参，避免 & 问题
# 注意：Python 命令行里的 & 会被 CMD 解析
# 所以用分号 ; 分隔命令
# 或者用 python dl.py url dest 方式

# 先检查 dl.py 内容
tid_check = submit('type C:\\installers\\dl.py')
time.sleep(5)
d_check = wait(tid_check)
print(f"   dl.py 内容:\n{d_check.get('stdout','')[:300]}")

print("\n" + "="*60)
