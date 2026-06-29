#!/usr/bin/env python3
"""Check Windows-mobile startup mechanisms"""
import json, urllib.request, base64

powershell_code = r'''
Write-Host "=== SCHTASKS (computehub*) ==="
schtasks /query /tn "computehub*" /v 2>nul
Write-Host ""
Write-Host "=== HKLM RUN ==="
reg query "HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" 2>nul
Write-Host ""
Write-Host "=== HKCU RUN ==="
reg query "HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Run" 2>nul
Write-Host ""
Write-Host "=== STARTUP FOLDER ==="
dir "C:\Users\*\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup" 2>nul
Write-Host ""
Write-Host "=== SERVICES ==="
sc query computehub 2>nul
sc query state= all 2>nul | findstr /i computehub
Write-Host ""
Write-Host "=== WMIC STARTUP ==="
wmic startup get caption,command 2>nul | findstr /i computehub
Write-Host ""
Write-Host "=== PROCESS OWNER ==="
wmic process where "name='computehub.exe'" get processid,executablepath,commandline 2>nul
'''

utf16 = powershell_code.encode('utf-16-le')
encoded = base64.b64encode(utf16).decode()

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

# If task submitted, poll for completion
if result.get('success') and result.get('data', {}).get('task_id'):
    task_id = result['data']['task_id']
    print(f"\nTask ID: {task_id}")
    print("Polling for result...")
    
    import time
    for i in range(10):
        time.sleep(3)
        poll_req = urllib.request.Request(
            f'http://36.250.122.43:8282/api/v1/tasks/status?id={task_id}'
        )
        poll_resp = urllib.request.urlopen(poll_req, timeout=10)
        poll_result = json.loads(poll_resp.read())
        status = poll_result.get('data', {}).get('status', '')
        result_output = poll_result.get('data', {}).get('result', '')
        print(f"  [{i+1}] status={status}")
        if status in ('completed', 'failed', 'timeout'):
            print("\n=== RESULT ===")
            print(result_output)
            break
