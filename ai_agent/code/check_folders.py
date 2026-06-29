#!/usr/bin/env python3
"""Check big folders on Windows-mobile"""
import json, urllib.request

task = {
    'node_id': 'Windows-mobile',
    'command': r'cmd /c echo === DESKTOP === && dir "C:\Users\Administrator\Desktop" /s /-c 2>nul | findstr "File(s)" && echo === PROGRAMS === && dir "C:\Program Files" /s /-c 2>nul | findstr "File(s)" | findstr /v "Dir" && echo === PROGRAMS86 === && dir "C:\Program Files (x86)" /s /-c 2>nul | findstr "File(s)" | findstr /v "Dir" && echo === TEMP === && dir C:\Windows\Temp /s /-c 2>nul | findstr "File(s)"',
    'timeout': 30,
    'priority': 10
}
req = urllib.request.Request(
    'http://36.250.122.43:8282/api/v1/tasks/submit',
    data=json.dumps(task).encode(),
    headers={'Content-Type': 'application/json'}
)
result = json.loads(urllib.request.urlopen(req, timeout=10).read())
print(result.get('data', {}).get('task_id', ''))
