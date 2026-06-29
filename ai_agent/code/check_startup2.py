#!/usr/bin/env python3
"""直接cmd查询启动方式，绕过PS管道问题"""
import json, urllib.request, base64

cmd_script = r'''
echo === SCHTASKS ===
schtasks /query /v /fo LIST 2>nul | findstr /i "compute"
echo.
echo === HKLM RUN ===
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /s 2>nul
echo.
echo === HKCU RUN ===
reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" /s 2>nul
echo.
echo === SERVICES ===
sc query state= all 2>nul | find /i "SERVICE_NAME: compute"
echo.
echo === PROCESS PATH ===
wmic process where "name='computehub.exe'" get executablepath /format:csv 2>nul
echo.
echo === DIR System32 ===
dir C:\Windows\System32\computehub.exe 2>nul
'''

# Use cmd directly via base64 EncodedCommand
encoded = base64.b64encode(cmd_script.encode('utf-16-le')).decode()

task = {
    'node_id': 'Windows-mobile',
    'command': f'powershell -EncodedCommand {encoded}',
    'timeout': 30,
    'priority': 8,
    'max_retries': 2
}

req = urllib.request.Request(
    'http://36.250.122.43:8282/api/v1/tasks/submit',
    data=json.dumps(task).encode(),
    headers={'Content-Type': 'application/json'}
)
resp = urllib.request.urlopen(req, timeout=15)
result = json.loads(resp.read())
print(json.dumps(result, indent=2, ensure_ascii=False))

if result.get('success') and result.get('data', {}).get('task_id'):
    task_id = result['data']['task_id']
    print(f"\nTask ID: {task_id}")
    print("Waiting 5s...")
    import time
    time.sleep(5)
    
    detail_req = urllib.request.Request(
        f'http://36.250.122.43:8282/api/v1/tasks/detail?task_id={task_id}'
    )
    detail_resp = urllib.request.urlopen(detail_req, timeout=10)
    detail = json.loads(detail_resp.read())
    data = detail.get('data', {})
    print(f"Status: {data.get('status')}")
    print(f"Exit: {data.get('exit_code')}")
    print(f"\nStdout:\n{data.get('stdout', '')}")
    if data.get('stderr'):
        print(f"\nStderr (first 500):\n{data['stderr'][:500]}")
