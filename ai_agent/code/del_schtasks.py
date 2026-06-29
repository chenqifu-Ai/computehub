#!/usr/bin/env python3
"""Delete 5 stale/duplicate scheduled tasks on Windows-mobile"""
import json, urllib.request, base64

tasks_to_delete = [
    "CHStart",
    "CHLogon",
    "ComputeHubStart",
    "ComputeHubLogon",
    "computehub-upgrade"
]

# Build PowerShell script to delete all 5 tasks
ps_lines = []
for t in tasks_to_delete:
    ps_lines.append(f'schtasks /delete /tn "\\{t}" /f')
    ps_lines.append(f'if %errorlevel% neq 0 (echo FAIL_{t}) else (echo OK_{t})')

ps_code = '\n'.join(ps_lines)
encoded = base64.b64encode(ps_code.encode('utf-16-le')).decode()

task = {
    'node_id': 'Windows-mobile',
    'command': f'powershell -EncodedCommand {encoded}',
    'timeout': 20,
    'priority': 10,
    'max_retries': 1
}

req = urllib.request.Request(
    'http://36.250.122.43:8282/api/v1/tasks/submit',
    data=json.dumps(task).encode(),
    headers={'Content-Type': 'application/json'}
)
result = json.loads(urllib.request.urlopen(req, timeout=15).read())
print(json.dumps(result, indent=2, ensure_ascii=False))
