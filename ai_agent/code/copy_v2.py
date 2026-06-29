#!/usr/bin/env python3
"""Copy computehub.exe to C:\ and update start.bat"""
import json, urllib.request, base64

# Use raw string to avoid escape issues
ps = r'copy /Y C:\Windows\System32\computehub.exe C:\computehub.exe && echo COPY_OK || echo COPY_FAIL'
b64 = base64.b64encode(ps.encode('utf-16-le')).decode()

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
