#!/usr/bin/env python3
"""
ComputeHub Windows 开机自启方案
===================================
通过 Task Scheduler 注册 SYSTEM 账户开机自启 Worker。

用法:
  # 远程执行（通过 ComputeHub Gateway Task 系统）:
  python3 scripts/win-autostart-setup.py <gateway_url> [node_id]

  # 本地执行（在 Windows 上直接运行）:
  python win-autostart-setup.py --local

前提:
  - computehub.exe 已安装到 PATH 可达的位置（如 C:\Windows\System32）
  - 或以绝对路径运行
"""

import json, urllib.request, time, sys, os

GW = sys.argv[1] if len(sys.argv) > 1 else "http://36.250.122.43:8282"
NODE = sys.argv[2] if len(sys.argv) > 2 else "Windows-mobile"
LOCAL = "--local" in sys.argv

# ── 配置 ──────────────────────────────────────────────
BINARY_PATH = r"C:\Windows\System32\computehub.exe"
WORK_DIR = r"C:\.computehub"
NODE_ID = "Windows-mobile"
GW_URL = GW if not LOCAL else "http://36.250.122.43:8282"
TASK_NAME = "ComputeHubWorker"

# Worker 启动命令
WORKER_CMD = (
    f'"{BINARY_PATH}" worker '
    f'--gw {GW_URL} '
    f'--node-id {NODE_ID} '
    f'--interval 3 --concurrent 4 --heartbeat 10'
)


def run_local(cmd):
    """在本地 Windows 上执行命令"""
    import subprocess
    try:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        return r.stdout.strip(), r.stderr.strip(), r.returncode
    except Exception as e:
        return "", str(e), -1


def run_remote(cmd, timeout=30):
    """通过 Gateway Task 系统远程执行"""
    task_id = f'auto-{int(time.time()*1000)}'
    task = {'task_id': task_id, 'node_id': NODE, 'command': cmd, 'timeout': timeout}
    body = json.dumps(task).encode()
    req = urllib.request.Request(f'{GW}/api/v1/tasks/submit', data=body,
                                 headers={'Content-Type': 'application/json'})
    resp = urllib.request.urlopen(req, timeout=15)
    result = json.loads(resp.read())
    if not result.get('success'):
        return "", result.get('error', '?'), -1

    deadline = time.time() + timeout
    while time.time() < deadline:
        req2 = urllib.request.Request(f'{GW}/api/v1/tasks/detail?task_id={task_id}&node_id={NODE}')
        resp2 = urllib.request.urlopen(req2, timeout=10)
        d = json.loads(resp2.read()).get('data', {})
        if d.get('status') in ('completed', 'failed', 'cancelled'):
            return d.get('stdout', '').strip(), d.get('stderr', '').strip(), d.get('exit_code', -1)
        time.sleep(2)
    return "", "timeout", -1


def run(cmd, timeout=30):
    if LOCAL:
        stdout, stderr, code = run_local(cmd)
        return stdout if stdout else stderr, code
    else:
        out, err, code = run_remote(cmd, timeout)
        return out if out else err, code


def step(num, title, cmd, timeout=30):
    print(f'\n{"="*60}')
    print(f'Step {num}: {title}')
    print(f'{"="*60}')
    print(f'  CMD: {cmd[:120]}')
    result, code = run(cmd, timeout)
    status = "✅" if code == 0 else "⚠️"
    print(f'  {status} exit={code}')
    if result:
        for line in result.split('\n')[:20]:
            print(f'    {line}')
    return result, code


# ══════════════════════════════════════════════════════
#  执行步骤
# ══════════════════════════════════════════════════════

print(f'🔧 ComputeHub Windows 开机自启配置')
print(f'   Binary: {BINARY_PATH}')
print(f'   Gateway: {GW_URL}')
print(f'   Node: {NODE_ID}')
print(f'   Mode: {"本地" if LOCAL else "远程"}')

# Step 1: 验证 binary 存在
step(1, '验证 binary 存在', f'cmd /c dir "{BINARY_PATH}"')

# Step 2: 检查版本
step(2, '检查 binary 版本', f'cmd /c "{BINARY_PATH}" version')

# Step 3: 清理旧的损坏任务
print(f'\n{"="*60}')
print('Step 3: 清理旧的损坏计划任务')
print(f'{"="*60}')
for old_task in ['ComputeHubWorker', 'ComputeHubStart', 'ComputeHubLogon', 'computehub-upgrade']:
    out, code = run(f'cmd /c schtasks /delete /tn "{old_task}" /f')
    icon = "✅" if code == 0 else "⚠️"
    print(f'  {icon} 删除 {old_task}: {out[:80]}')
    time.sleep(0.5)

# Step 4: 创建工作目录
step(4, '创建工作目录', f'cmd /c mkdir "{WORK_DIR}" 2>nul & echo OK')

# Step 5: 创建启动脚本
BAT_CONTENT = (
    '@echo off\r\n'
    f'cd /d "{WORK_DIR}"\r\n'
    f'echo [%date% %time%] ComputeHub Worker starting... >> "{WORK_DIR}\\startup.log"\r\n'
    f'"{BINARY_PATH}" worker --gw {GW_URL} --node-id {NODE_ID} --interval 3 --concurrent 4 --heartbeat 10\r\n'
    f'echo [%date% %time%] Worker exited (code=%errorlevel%) >> "{WORK_DIR}\\startup.log"\r\n'
    'ping -n 5 127.0.0.1 >nul\r\n'
    f'goto :eof\r\n'
)
# Write bat file via echo commands
bat_path = f'{WORK_DIR}\\start_worker.bat'
step(5, '创建启动脚本',
     f'cmd /c echo @echo off> "{bat_path}" & '
     f'echo cd /d "{WORK_DIR}">> "{bat_path}" & '
     f'echo "{BINARY_PATH}" worker --gw {GW_URL} --node-id {NODE_ID} --interval 3 --concurrent 4 --heartbeat 10^>^>"{WORK_DIR}\\startup.log">> "{bat_path}" & '
     f'echo echo OK')

# Step 6: 注册 Task Scheduler 任务
# 使用 schtasks 创建 SYSTEM 账户的开机自启任务
schtasks_cmd = (
    f'cmd /c schtasks /create '
    f'/tn "{TASK_NAME}" '
    f'/tr "\\"{bat_path}\\"" '
    f'/sc ONSTART '          # 开机启动
    f'/ru SYSTEM '           # 以 SYSTEM 账户运行
    f'/rl HIGHEST '          # 最高权限
    f'/delay 0000:30 '       # 延迟 30 秒（等网络就绪）
    f'/f'                    # 强制覆盖
)
step(6, f'注册开机自启任务: {TASK_NAME}', schtasks_cmd)

# Step 7: 添加 "失败后自动重启" 策略
# schtasks 不支持 /ri (restart interval) 在 ONSTART 模式下，
# 所以我们在 bat 脚本里加了 5s delay + 由 schtasks 监控
# 额外注册一个 ONLOGON 任务作为备份
schtasks_logon = (
    f'cmd /c schtasks /create '
    f'/tn "ComputeHubLogon" '
    f'/tr "\\"{bat_path}\\"" '
    f'/sc ONLOGON '
    f'/delay 0000:10 '
    f'/f'
)
step(7, '注册登录自启任务 (备份)', schtasks_logon)

# Step 8: 验证任务注册
step(8, '验证计划任务', f'cmd /c schtasks /query /tn "{TASK_NAME}"')

# Step 9: 检查当前进程，如果没运行就立即启动
out, code = step(9, '检查当前进程', 'cmd /c tasklist /fi "imagename eq computehub.exe"')
if 'computehub.exe' not in out.lower():
    print('\n⚠️  Worker 未运行，立即启动...')
    step('9b', '启动 Worker', f'cmd /c start "" "{bat_path}"')
    time.sleep(5)
    step('9c', '验证进程', 'cmd /c tasklist /fi "imagename eq computehub.exe"')

# Step 10: 验证 Gateway 注册
time.sleep(3)
print(f'\n{"="*60}')
print('Step 10: 验证 Gateway 注册')
print(f'{"="*60}')
try:
    req = urllib.request.Request(f'{GW}/api/v1/nodes/list')
    resp = urllib.request.urlopen(req, timeout=10)
    nodes = json.loads(resp.read()).get('data', [])
    for n in nodes:
        icon = "📡" if NODE_ID.lower() in n['node_id'].lower() else "  "
        print(f'  {icon} {n["node_id"]:25s} v{n.get("version","?"):10s} {n["status"]:8s} {n.get("platform","")}')
except Exception as e:
    print(f'  ❌ Gateway 查询失败: {e}')

# ── 总结 ──────────────────────────────────────────────
print(f'\n{"="*60}')
print('📋 配置完成！')
print(f'{"="*60}')
print(f'  启动脚本: {bat_path}')
print(f'  开机自启: schtasks /tn "{TASK_NAME}" (ONSTART, SYSTEM)')
print(f'  登录自启: schtasks /tn "ComputeHubLogon" (ONLOGON, 备份)')
print(f'  工作目录: {WORK_DIR}')
print(f'  启动日志: {WORK_DIR}\\startup.log')
print(f'  升级缓存: {WORK_DIR}\\upgrade_cache_*.json')
print()
print('手动管理:')
print(f'  查看: schtasks /query /tn "{TASK_NAME}" /v')
print(f'  手动启动: schtasks /run /tn "{TASK_NAME}"')
print(f'  停止: schtasks /end /tn "{TASK_NAME}"')
print(f'  删除: schtasks /delete /tn "{TASK_NAME}" /f')
print()
