#!/usr/bin/env python3
"""
在 ECS 上提交任务到 Windows Worker → 调 Agent API → 拿回答
完全避开 shell 引号逃逸问题，用 Python http.client
"""
import json, sys, time

# 用 exec 直接通过 SSH 在 ECS 上跑 Python
SCRIPT = r"""
import urllib.request
import json

GW = "http://36.250.122.43:8282"
NODE = "windows-mobile"

# 构造 Agent 对话请求
task_payload = {
    "task_id": "agent-intro-v2",
    "node_id": NODE,
    "command": (
        'powershell -NoProfile -ExecutionPolicy Bypass -Command "'
        '$body = @{}; '
        '$body.task = \'你好，我是小智！初次见面，请自我介绍——你的节点ID、操作系统版本、compute版本号、你最擅长的3个能力。直接回答，不用调用工具。\'; '
        '$body.session_id = \'chat-final\'; '
        '$json = $body | ConvertTo-Json -Compress; '
        '$r = Invoke-RestMethod -Uri http://127.0.0.1:8383/api/v1/worker/think -Method Post -Body $json -ContentType application/json -UseBasicParsing; '
        'Write-Host ($r | ConvertTo-Json -Depth 5 -Compress)'
        '"'
    ),
    "timeout": 120
}

req = urllib.request.Request(
    f"{GW}/api/v1/tasks/submit",
    data=json.dumps(task_payload).encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)

resp = urllib.request.urlopen(req)
result = json.loads(resp.read())
print(f"SUBMIT: {json.dumps(result, ensure_ascii=False)}")

# 轮询结果
for i in range(40):
    time.sleep(3)
    try:
        detail_url = f"{GW}/api/v1/tasks/detail?task_id=agent-intro-v2&node_id={NODE}"
        detail_resp = urllib.request.urlopen(detail_url, timeout=5)
        detail = json.loads(detail_resp.read())
        data = detail.get("data", {})
        status = data.get("status", "")
        if status == "completed":
            print(f"\n=== AGENT 回答 ===")
            print(data.get("stdout", "")[:4000])
            print(f"\n=== 退出码: {data.get('exit_code')} ===")
            sys.exit(0)
        print(f"  [{i*3}s] status={status}")
    except Exception as e:
        print(f"  [{i*3}s] 等待中... ({e})")

print("超时")
"""

# 通过 SSH 传到 ECS 执行
import subprocess
ssh_cmd = [
    "ssh", "-o", "StrictHostKeyChecking=no", "-p", "8022",
    "-i", "/root/.ssh/id_ed25519_computehub",
    "computehub@36.250.122.43",
    f"python3 -c {json.dumps(SCRIPT)}"
]

result = subprocess.run(ssh_cmd, capture_output=True, text=True, timeout=300)
print("STDOUT:", result.stdout[:5000])
if result.stderr:
    print("STDERR:", result.stderr[:1000])