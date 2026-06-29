#!/usr/bin/env python3
"""Check disk space - separate simple queries"""
import json, urllib.request

cmds = [
    ('space', r'cmd /c wmic logicaldisk where drivetype=3 get deviceid,freespace,size /format:csv'),
    ('users', r'cmd /c dir C:\Users /s /-c 2>nul | findstr "File(s)"'),
    ('windows', r'cmd /c dir C:\Windows\System32 /s /-c 2>nul | findstr "File(s)" | findstr /v "Dir"'),
    ('temp', r'cmd /c dir C:\Windows\Temp /s /-c 2>nul | findstr "File(s)"'),
    ('appdata', r'cmd /c dir "C:\Users\Administrator\AppData" /s /-c 2>nul | findstr "File(s)"'),
    ('programs', r'cmd /c dir "C:\Program Files" /s /-c 2>nul | findstr "File(s)" | findstr /v "Dir"'),
    ('programs86', r'cmd /c dir "C:\Program Files (x86)" /s /-c 2>nul | findstr "File(s)" | findstr /v "Dir"'),
]

for name, cmd in cmds:
    task = {
        'node_id': 'Windows-mobile',
        'command': cmd,
        'timeout': 30,
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
    print(f'{name:15s} → {tid}')
