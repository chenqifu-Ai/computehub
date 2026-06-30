#!/usr/bin/env python3
import json, subprocess, base64, time

def submit(b64cmd, timeout=30):
    cmd = 'powershell -EncodedCommand ' + b64cmd
    r = subprocess.run(
        ['curl', '-s', '-m', '15', '-X', 'POST',
         'http://localhost:8282/api/v1/tasks/submit',
         '-H', 'Content-Type: application/json',
         '-d', json.dumps({'node_id': 'wanlida-opc01', 'task_type': 'exec_shell', 'command': cmd, 'timeout': timeout})],
        capture_output=True, text=True)
    return json.loads(r.stdout).get('data', {}).get('task_id', '')

def wait(tid, max_w=60):
    for _ in range(max_w * 2):
        time.sleep(1)
        r2 = subprocess.run(
            ['curl', '-s', '-m', '10', f'http://localhost:8282/api/v1/tasks/detail?task_id={tid}'],
            capture_output=True, text=True)
        d = json.loads(r2.stdout).get('data', {})
        if d.get('status') in ('completed', 'failed'):
            return d
    return {'status': 'timeout'}

# PowerShell 验证脚本（避免转义问题，用数组）
ps_lines = [
    'C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\python.exe --version',
    'C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -c "import json, sys; print(sys.version); print(\'WORKS\')"',
    'C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\Scripts\\pip.exe --version',
]

# 用PowerShell脚本块
ps_script = (
    '$r = @()\n'
    '$r += Get-Command C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\python.exe -ErrorAction SilentlyContinue\n'
    '$r += C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\python.exe --version 2>&1\n'
    '$r += C:\\Users\\admin\\AppData\\Local\\Programs\\Python\\Python312\\Scripts\\pip.exe --version 2>&1\n'
    '$r += [Environment]::GetEnvironmentVariable("PATH", "User")\n'
    '$r -join "`n"'
)

b64 = base64.b64encode(ps_script.encode('utf-16-le')).decode()
print(f"PS b64 len: {len(b64)}")

tid = submit(b64)
print(f'Task: {tid}')

for i in range(30):
    time.sleep(2)
    r = subprocess.run(
        ['curl', '-s', '-m', '10', f'http://localhost:8282/api/v1/tasks/detail?task_id={tid}'],
        capture_output=True, text=True)
    d = json.loads(r.stdout).get('data', {})
    if d.get('status') in ('completed', 'failed'):
        print(f"\n✅ 完成! exit={d.get('exit_code')} dur={d.get('duration')}")
        print(f"\n=== 输出 ===")
        print(d.get('stdout', ''))
        break
    elif i % 8 == 0:
        print(f"poll {i+1}...")
else:
    print("⏰ timeout")
