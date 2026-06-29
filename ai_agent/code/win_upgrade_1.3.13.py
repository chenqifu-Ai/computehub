#!/usr/bin/env python3
"""windows-mobile 升级到 v1.3.13 — WIN-COM-003 Base64 协议"""

import base64, json, urllib.request, time, sys

API = 'http://36.250.122.43:8282'
HEADERS = {'Content-Type': 'application/json'}
NODE = 'windows-mobile'

def submit(cmd, timeout=60):
    ts = int(time.time() * 1000)
    task = {
        'task_id': f'win-{ts}',
        'node_id': NODE,
        'command': cmd,
        'timeout': timeout
    }
    req = urllib.request.Request(f'{API}/api/v1/tasks/submit',
                                 data=json.dumps(task).encode(),
                                 headers=HEADERS)
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    tid = task['task_id']
    print(f'  → 已提交: {tid}')
    return tid

def wait_and_check(tid, wait=5):
    time.sleep(wait)
    req = urllib.request.Request(f'{API}/api/v1/tasks/detail?task_id={tid}')
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
    d = resp.get('data', {})
    if d:
        status = d.get('status', 'unknown')
        ec = d.get('exit_code', -1)
        out = d.get('stdout', '')
        err = d.get('stderr', '')
        print(f'  ← status={status} exit={ec}')
        if out:
            print(f'    stdout: {out[:400]}')
        if err:
            print(f'    stderr: {err[:200]}')
        return d
    else:
        print(f'  ← 无数据: {resp}')
        return None

# ────────────────────────────────────────────
# 步骤1: 用 PowerShell 下载新 binary
# ────────────────────────────────────────────
print('═══ 步骤1: 下载 v1.3.13 binary ═══')

# Base64 编码 PowerShell 脚本
ps_download = '''
$url = 'http://36.250.122.43:8282/api/v1/files/computehub-windows-amd64.exe'
$out = 'C:\\Windows\\Temp\\ch_new.exe'
try {
    [Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
    $wc = New-Object System.Net.WebClient
    $wc.DownloadFile($url, $out)
    $f = Get-Item $out
    Write-Host ("OK:" + $f.Length)
} catch {
    Write-Host ("FAIL:" + $_.Exception.Message)
}
'''

b64 = base64.b64encode(ps_download.encode('utf-16-le')).decode()
cmd = f'powershell -noprofile -ExecutionPolicy Bypass -Command "$b=\'{b64}\';$d=[System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String($b));iex $d"'

tid1 = submit(cmd, timeout=120)
d1 = wait_and_check(tid1, wait=12)

if d1 and d1.get('exit_code') == 0:
    out = d1.get('stdout', '')
    if 'OK:' in out:
        size = out.split('OK:')[1].strip()
        print(f'  ✅ 下载成功 ({size} bytes)')
    else:
        print(f'  ⚠️  下载可能失败: {out}')
        # 试试 curl
        print('  尝试 curl 备用方案...')
        tid1b = submit('curl -s -o C:\\Windows\\Temp\\ch_new.exe http://36.250.122.43:8282/api/v1/files/computehub-windows-amd64.exe && echo OK', timeout=120)
        d1b = wait_and_check(tid1b, wait=10)
        if not (d1b and d1b.get('exit_code') == 0):
            print('  ❌ 下载失败，退出')
            sys.exit(1)
else:
    print(f'  ❌ 下载失败 (exit={d1.get("exit_code") if d1 else "N/A"})')
    sys.exit(1)

# ────────────────────────────────────────────
# 步骤2: 写升级脚本
# ────────────────────────────────────────────
print('\n═══ 步骤2: 写升级脚本 ═══')

# schtasks 升级脚本 — 写入临时目录，然后通过 schtasks 延迟执行
upgrade_bat = '''
@echo off
cd /d C:\\Windows\\System32
echo [%DATE% %TIME%] 升级到 v1.3.13 >> C:\\Windows\\Temp\\ch_upgrade.log
echo [%DATE% %TIME%] 停止旧进程... >> C:\\Windows\\Temp\\ch_upgrade.log
taskkill /F /IM computehub.exe /T >> C:\\Windows\\Temp\\ch_upgrade.log 2>&1
timeout /t 3 /nobreak >nul
echo [%DATE% %TIME%] 替换 binary... >> C:\\Windows\\Temp\\ch_upgrade.log
copy /Y C:\\Windows\\Temp\\ch_new.exe computehub.exe >> C:\\Windows\\Temp\\ch_upgrade.log 2>&1
echo [%DATE% %TIME%] 删除临时文件 >> C:\\Windows\\Temp\\ch_upgrade.log
del C:\\Windows\\Temp\\ch_new.exe
echo [%DATE% %TIME%] 启动新 Worker... >> C:\\Windows\\Temp\\ch_upgrade.log
start /B computehub.exe worker --gw http://36.250.122.43:8282 --node-id windows-mobile --interval 3 --concurrent 4 --heartbeat 10
echo [%DATE% %TIME%] 升级完成 >> C:\\Windows\\Temp\\ch_upgrade.log
'''

bat_b64 = base64.b64encode(upgrade_bat.encode('utf-16-le')).decode()
cmd2 = f'powershell -noprofile -ExecutionPolicy Bypass -Command "$b=\'{bat_b64}\';$d=[System.Text.Encoding]::Unicode.GetString([System.Convert]::FromBase64String($b));Set-Content -Path C:\\Windows\\Temp\\ch_upgrade.bat -Value $d -Encoding Unicode;Write-Host BAT_OK"'

tid2 = submit(cmd2, timeout=30)
d2 = wait_and_check(tid2, wait=3)
if d2 and d2.get('exit_code') == 0 and 'BAT_OK' in d2.get('stdout', ''):
    print('  ✅ 脚本写入成功')
else:
    # 试试 echo 方案写入
    print('  ⚠️ PowerShell 写入失败，尝试 echo 方案...')
    cmd2b = (
        'echo @echo off > C:\\Windows\\Temp\\ch_upgrade.bat && '
        'echo taskkill /F /IM computehub.exe /T >> C:\\Windows\\Temp\\ch_upgrade.bat && '
        'echo timeout /t 3 /nobreak >> C:\\Windows\\Temp\\ch_upgrade.bat && '
        'echo copy /Y C:\\Windows\\Temp\\ch_new.exe C:\\Windows\\System32\\computehub.exe >> C:\\Windows\\Temp\\ch_upgrade.bat && '
        'echo del C:\\Windows\\Temp\\ch_new.exe >> C:\\Windows\\Temp\\ch_upgrade.bat && '
        'echo start /B C:\\Windows\\System32\\computehub.exe worker --gw http://36.250.122.43:8282 --node-id windows-mobile --interval 3 --concurrent 4 --heartbeat 10 >> C:\\Windows\\Temp\\ch_upgrade.bat && '
        'echo BAT_OK'
    )
    tid2b = submit(cmd2b, timeout=30)
    d2b = wait_and_check(tid2b, wait=3)
    if d2b and d2b.get('exit_code') == 0 and 'BAT_OK' in d2b.get('stdout', ''):
        print('  ✅ echo 方案写入成功')
    else:
        print(f'  ❌ 脚本写入全部失败: {d2b}')
        sys.exit(1)

# ────────────────────────────────────────────
# 步骤3: 用 schtasks 调度升级（延迟 10 秒，确保当前任务先返回）
# ────────────────────────────────────────────
print('\n═══ 步骤3: schtasks 延迟执行升级 ═══')

cmd3 = (
    'schtasks /create /tn "ComputeHub_Upgrade" /tr "C:\\Windows\\Temp\\ch_upgrade.bat" '
    '/sc once /st 00:00 /sd 01/01/2026 /f /ru SYSTEM && '
    'schtasks /run /tn "ComputeHub_Upgrade" && '
    'echo SCHTASKS_OK'
)

tid3 = submit(cmd3, timeout=30)
d3 = wait_and_check(tid3, wait=5)
if d3 and d3.get('exit_code') == 0 and 'SCHTASKS_OK' in d3.get('stdout', ''):
    print('  ✅ schtasks 已调度升级！Worker 将在几秒后重启')
else:
    print(f'  ⚠️  schtasks 调度结果: exit={d3.get("exit_code")} out={d3.get("stdout","")[:300] if d3 else "N/A"}')
    # 直接执行 bat
    print('  尝试直接执行 bat...')
    cmd3b = 'start /B C:\\Windows\\Temp\\ch_upgrade.bat && echo DIR_OK'
    tid3b = submit(cmd3b, timeout=30)
    d3b = wait_and_check(tid3b, wait=5)
    print(f'  直接执行: exit={d3b.get("exit_code") if d3b else "N/A"}')

# ────────────────────────────────────────────
# 等待并验证
# ────────────────────────────────────────────
print(f'\n═══ 等待 20 秒让升级完成... ═══')
time.sleep(20)

print(f'\n═══ 验证升级结果 ═══')
req = urllib.request.Request(f'{API}/api/v1/nodes/list')
resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
for n in resp['data']:
    if 'windows' in n['node_id'].lower():
        print(f'{n["node_id"]:20s} {n["status"]:10s} v{n["version"]:10s} {n["platform"]}')

# 如果能连通，再发个测试任务
if any(n['status'] == 'online' and 'windows' in n['node_id'].lower() for n in resp['data']):
    print('\n═══ 发送验证任务 ═══')
    tid_v = submit('computehub version', timeout=15)
    d_v = wait_and_check(tid_v, wait=5)
    if d_v:
        print(f'版本: {d_v.get("stdout","")[:100]}')
        if 'v1.3.13' in d_v.get('stdout', ''):
            print('\n🎉 升级成功！windows-mobile 已到 v1.3.13')
        else:
            print('\n⚠️ 版本可能未更新')
    else:
        print('\n❌ 验证任务失败')
else:
    print('\n⚠️ windows-mobile 还未上线')
    print('  可能需要手动重启 Worker')
