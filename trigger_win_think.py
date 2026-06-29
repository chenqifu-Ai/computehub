#!/usr/bin/env python3
"""Trigger Windows-mobile Agent think via Gateway task dispatch."""
import json, time, base64, subprocess, sys

ps_code = (
    '$bodyJson = "{'
    '\\"task\\":\\"你是谁\\",'
    '\\"session_id\\":\\"win-think\\"'
    '}"\n'
    '$bytes = [System.Text.Encoding]::UTF8.GetBytes($bodyJson)\n'
    '$result = Invoke-RestMethod -Uri http://127.0.0.1:8383/api/v1/worker/think '
    '-Method POST -Body $bytes -ContentType "application/json"\n'
    '$result.answer\n'
)

encoded = base64.b64encode(ps_code.encode("utf-16le")).decode()
cmd = f"powershell -NoProfile -NonInteractive -EncodedCommand {encoded}"

payload = json.dumps({
    "task_id": "win-think-11",
    "node_id": "Windows-mobile",
    "command": cmd,
    "timeout": 120,
    "type": "shell"
})

# Submit
r = subprocess.run(["ssh", "-p", "8022", "-i", "/root/.ssh/id_ed25519_computehub",
    "computehub@36.250.122.43",
    f'curl -s -X POST http://127.0.0.1:8282/api/v1/tasks/submit -H "Content-Type: application/json" -d \'{payload}\''
], capture_output=True, text=True)
print("SUBMIT:", r.stdout.strip())

# Wait
time.sleep(40)

# Get result
r2 = subprocess.run(["ssh", "-p", "8022", "-i", "/root/.ssh/id_ed25519_computehub",
    "computehub@36.250.122.43",
    'curl -s "http://127.0.0.1:8282/api/v1/tasks/progress?task_id=win-think-11"'
], capture_output=True, text=True)

try:
    data = json.loads(r2.stdout).get("data", {})
    print(f"exit={data.get('exit_code')} dur={data.get('duration')} running={data.get('running')}")
    stdout = data.get("stdout", "")
    if stdout:
        print("=== STDOUT ===")
        print(stdout[:3000])
    stderr = data.get("stderr", "")
    if stderr:
        print("=== STDERR ===")
        print(stderr[:500])
except Exception as e:
    print(f"Parse error: {e}")
    print(r2.stdout[:1000])