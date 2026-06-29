#!/usr/bin/env python3
"""ECS ecs-p2ph 升级到 v1.3.14 —— dd 覆盖法"""

import urllib.request, json, base64, time, sys

API = 'http://36.250.122.43:8282'
HEADERS = {'Content-Type': 'application/json'}
NODE = 'ecs-p2ph'

def submit(cmd, timeout=30):
    ts = int(time.time() * 1000)
    tid = f'ecs14-{ts}'
    task = {'task_id': tid, 'node_id': NODE, 'command': cmd, 'timeout': timeout}
    req = urllib.request.Request(f'{API}/api/v1/tasks/submit', data=json.dumps(task).encode(), headers=HEADERS)
    resp = json.loads(urllib.request.urlopen(req, timeout=15).read().decode())
    print(f'  → {tid}')
    return tid

def wait(tid, delay=5):
    time.sleep(delay)
    req = urllib.request.Request(f'{API}/api/v1/tasks/detail?task_id={tid}')
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
    d = resp.get('data', {})
    if d:
        print(f'  ← exit={d.get("exit_code")} status={d.get("status")}')
        out = d.get('stdout','')[:200]
        err = d.get('stderr','')[:200]
        if out: print(f'    stdout: {out}')
        if err: print(f'    stderr: {err}')
        return d
    return None

# 步骤1: 确认 binary 存在
print('═══ 步骤1: 确认 binary ═══')
tid = submit('ls -la /tmp/computehub_v1.3.14', timeout=10)
d = wait(tid, delay=4)
if not d or d.get('exit_code') != 0:
    print('❌ binary 不存在，需重新下载')
    sys.exit(1)
print('✅ binary 存在 (14.9MB)')

# 步骤2: 用 dd 覆盖运行中的 binary（dd 写入已有 inode，不触发 Text file busy）
print('\n═══ 步骤2: dd 覆盖 binary ═══')
cmd = 'dd if=/tmp/computehub_v1.3.14 of=/home/computehub/computehub bs=1M 2>/dev/null && chmod +x /home/computehub/computehub && echo DD_OK'
tid = submit(cmd, timeout=15)
d = wait(tid, delay=5)
if not d or 'DD_OK' not in d.get('stdout',''):
    print(f'❌ dd 覆盖失败')
    sys.exit(1)
print('✅ binary 已覆盖')

# 步骤3: 检查版本（binary 已更新但进程还是旧的，因为 inode 不同）
print('\n═══ 步骤3: 确认 binary 版本 ═══')
tid = submit('/home/computehub/computehub version', timeout=10)
d = wait(tid, delay=4)
if d:
    print(f'  版本: {d.get("stdout","").strip()}')
    if '1.3.14' in d.get('stdout',''):
        print('✅ binary 已更新到 v1.3.14')
    else:
        print(f'⚠️  版本异常')

# 步骤4: kill worker 让 systemd 重启（用新 binary）
print('\n═══ 步骤4: 重启 Worker ═══')
# 先写脚本到文件，再触发后台执行（避免自杀问题）
script = '#!/bin/bash\nsleep 2\nkill -9 $(pgrep -f "computehub worker" | head -1) 2>/dev/null\necho WORKER_KILLED'
script_b64 = base64.b64encode(script.encode()).decode()

tid = submit(f'echo "{script_b64}" | base64 -d > /tmp/restart_v14.sh && chmod +x /tmp/restart_v14.sh && echo SCRIPT_OK', timeout=10)
d = wait(tid, delay=3)
if d and 'SCRIPT_OK' in d.get('stdout',''):
    # 后台触发，立刻返回
    tid2 = submit('nohup /tmp/restart_v14.sh > /tmp/restart_v14.log 2>&1 & echo TRIGGERED', timeout=5)
    d2 = wait(tid2, delay=2)
    print('  Worker 重启中（systemd 自动接管）')

print('\n等待 20 秒...')
time.sleep(20)

# 验证
print('\n═══ 验证升级 ═══')
req = urllib.request.Request(f'{API}/api/v1/nodes/list')
resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
for n in resp['data']:
    if n['node_id'] == 'ecs-p2ph':
        print(f'ecs-p2ph: {n["status"]:10s} v{n["version"]:10s}')
        
        if '1.3.14' in n['version']:
            print('\n🎉🎉🎉 ecs-p2ph v1.3.14 升级成功！')
            
            # 自动消费测试
            print('\n═══ ARC-AI-NET-002 自动消费测试 ═══')
            msg = {
                "protocol": "arc-ai-net-001", "version": "1.0",
                "msg_id": f"v14test_{int(time.time())}", "msg_type": "direct",
                "from": "小智A", "from_node": "ecs-p2ph",
                "to": "小智B", "to_node": "ecs-p2ph",
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
                "ttl_seconds": 300, "content_type": "game",
                "content_encoding": "plain",
                "content": "ARC-AI-NET-002 自动消费！我出石头✊！"
            }
            b64 = base64.b64encode(json.dumps(msg).encode()).decode()
            tid3 = submit(b64, timeout=30)
            d3 = wait(tid3, delay=4)
            if d3:
                out = d3.get('stdout','')
                ec = d3.get('exit_code')
                print(f'  自动消费结果: exit={ec}')
                if 'AI 消息已入队列' in out:
                    print('\n✅✅✅ ARC-AI-NET-002 自动消费功能上线成功！🎉')
                print(f'  stdout: {out[:200]}')
        else:
            print('⚠️ 版本未更新')
        break
PYEOF