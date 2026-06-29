#!/usr/bin/env python3
"""Check windows-mobile status via Gateway"""
import json, urllib.request, base64, sys, time

GW = 'http://36.250.122.43:8282'

def enc(cmd):
    return base64.b64encode(cmd.encode('utf-16le')).decode()

def submit(nid, cmd, timeout=60):
    task = {'node_id': nid, 'command': f'powershell -EncodedCommand {enc(cmd)}', 'timeout': timeout, 'priority': 10}
    req = urllib.request.Request(f'{GW}/api/v1/tasks/submit', data=json.dumps(task).encode(),
                                  headers={'Content-Type': 'application/json'}, method='POST')
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def wait_detail(tid, max_sec=30):
    for i in range(max_sec // 2):
        with urllib.request.urlopen(f'{GW}/api/v1/tasks/detail?task_id={tid}', timeout=10) as resp:
            d = json.loads(resp.read())
        st = d.get('data', {}).get('status', '')
        out = d.get('data', {}).get('output', '')
        ec = d.get('data', {}).get('exit_code', -1)
        if st in ('completed', 'failed'):
            return out, ec, st
        time.sleep(2)
    return '', -2, 'timeout'

# Check computehub process + files
cmd = '''
$p = Get-Process computehub -ErrorAction SilentlyContinue
if ($p) {
    Write-Output "computehub PID: $($p.Id)"
} else {
    Write-Output "No computehub process"
}
Write-Output "=== C: drive files ==="
$files = Get-ChildItem "C:\\computehub*.exe" -ErrorAction SilentlyContinue
if ($files) {
    $files | ForEach-Object { Write-Output ("  " + $_.Name + " - " + $_.Length + " bytes - " + $_.LastWriteTime) }
} else {
    Write-Output "  No computehub*.exe found on C:"
}
Write-Output "=== D: drive ==="
if (Test-Path "D:\\") {
    $files = Get-ChildItem "D:\\computehub*.exe" -ErrorAction SilentlyContinue
    if ($files) {
        $files | ForEach-Object { Write-Output ("  " + $_.Name + " - " + $_.Length + " bytes") }
    } else { Write-Output "  No computehub*.exe found on D:" }
} else { Write-Output "  No D: drive" }
'''

r = submit('windows-mobile', cmd, 20)
if r.get('success'):
    tid = r['data']['task_id']
    print(f'Task: {tid}')
    out, ec, st = wait_detail(tid, 30)
    print(f'Status: {st}, Exit: {ec}')
    if out.strip():
        print(out)
    else:
        # try to get full detail including stderr
        with urllib.request.urlopen(f'{GW}/api/v1/tasks/detail?task_id={tid}', timeout=10) as resp:
            d = json.loads(resp.read())
        dd = d.get('data', {})
        print('stderr:', (dd.get('stderr') or '')[:500])
else:
    print('FAIL:', r)