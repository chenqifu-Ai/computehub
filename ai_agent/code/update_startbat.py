#!/usr/bin/env python3
"""Update start.bat to use C:\computehub.exe"""
import json, urllib.request, base64

# PowerShell script to rewrite start.bat - use pre-encoded to avoid $ issues
ps_lines = [
    r"""$content = '@echo off"""
    r"""cd /d C:\computehub"""
    r"""C:\computehub.exe worker --gw http://36.250.122.43:8282 --node-id Windows-mobile --interval 3 --concurrent 4 --heartbeat 10"""
    r"""'"""
    r"""Set-Content -Path C:\computehub\start.bat -Value $content -Force"""
    r"""Write-Host "DONE" """
]

b64 = base64.b64encode(('\n'.join(ps_lines)).encode('utf-16-le')).decode()

task = {
    'node_id': 'Windows-mobile',
    'command': f'powershell -EncodedCommand {b64}',
    'timeout': 15,
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
