#!/usr/bin/env python3
"""Check startup bat files and binary locations"""
import json, urllib.request

queries = [
    ('start-admin', 'cmd /c dir C:\\Users\\administrator\\start.bat 2>nul && type C:\\Users\\administrator\\start.bat'),
    ('start-computehub', 'cmd /c dir C:\\computehub\\start.bat 2>nul && type C:\\computehub\\start.bat'),
    ('dir-admin', 'cmd /c dir C:\\Users\\administrator\\computehub.exe 2>nul'),
    ('dir-computehub-folder', 'cmd /c dir C:\\computehub 2>nul'),
]

for name, cmd in queries:
    task = {
        'node_id': 'Windows-mobile',
        'command': cmd,
        'timeout': 10,
        'priority': 10,
        'max_retries': 0
    }
    req = urllib.request.Request(
        'http://36.250.122.43:8282/api/v1/tasks/submit',
        data=json.dumps(task).encode(),
        headers={'Content-Type': 'application/json'}
    )
    result = json.loads(urllib.request.urlopen(req, timeout=10).read())
    tid = result.get('data', {}).get('task_id', '')
    print(f'{name:25s} → {tid}')
