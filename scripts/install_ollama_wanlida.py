#!/usr/bin/env python3
"""在 wanlida-work01 安装 Ollama"""

import json
import urllib.request
import base64
import time

GATEWAY = 'http://127.0.0.1:8282'
NODE = 'wanlida-work01'

# PowerShell 安装脚本
ps_script = r'''
$installer = 'C:\Users\admin\Downloads\OllamaSetup.exe'
if (Test-Path $installer) {
    Write-Host 'Starting Ollama installation...'
    # 静默安装
    Start-Process -FilePath $installer -ArgumentList '/S', '/D=C:\Users\admin\AppData\Local\Programs\Ollama' -Wait
    Write-Host 'Installation finished'
    
    # 检查安装结果
    if (Test-Path 'C:\Users\admin\AppData\Local\Programs\Ollama\ollama.exe') {
        Write-Host 'SUCCESS: Ollama installed to AppData'
        & 'C:\Users\admin\AppData\Local\Programs\Ollama\ollama.exe' --version
    } elseif (Test-Path 'C:\Program Files\Ollama\ollama.exe') {
        Write-Host 'SUCCESS: Ollama installed to Program Files'
        & 'C:\Program Files\Ollama\ollama.exe' --version
    } else {
        Write-Host 'WARNING: Installation finished but ollama.exe not found in standard locations'
        Get-ChildItem 'C:\Users\admin\AppData\Local\Programs' -Recurse -Filter 'ollama.exe' -ErrorAction SilentlyContinue
    }
} else {
    Write-Host 'ERROR: Installer not found at' $installer
    exit 1
}
'''

# Base64 编码
b64 = base64.b64encode(ps_script.encode('utf-16le')).decode()

# 提交任务
payload = {
    'node_id': NODE,
    'command': f'powershell -EncodedCommand {b64}',
    'timeout': 300
}

print(f'[1/2] 提交安装任务到 {NODE}...')
req = urllib.request.Request(
    f'{GATEWAY}/api/v1/tasks/submit',
    data=json.dumps(payload).encode(),
    headers={'Content-Type': 'application/json'}
)

resp = urllib.request.urlopen(req, timeout=30)
result = json.loads(resp.read())
task_id = result.get('data', {}).get('task_id')
print(f'      Task ID: {task_id}')

# 轮询结果
print(f'[2/2] 等待安装完成（最长 5 分钟）...')
start = time.time()
while time.time() - start < 300:
    url = f"{GATEWAY}/api/v1/tasks/detail?task_id={task_id}"
    resp = urllib.request.urlopen(url, timeout=10)
    data = json.loads(resp.read())
    task = data.get('data', {})
    status = task.get('status', 'unknown')
    
    if status in ('completed', 'success', 'failed', 'error'):
        print(f'\n结果: {status}')
        print(f'退出码: {task.get("exit_code")}')
        if task.get('stdout'):
            print(f'输出:\n{task["stdout"]}')
        if task.get('stderr'):
            print(f'错误:\n{task["stderr"]}')
        break
    
    time.sleep(3)
    print('.', end='', flush=True)
else:
    print('\n超时！')