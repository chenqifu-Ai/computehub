#!/usr/bin/env python3
"""生成 PowerShell -EncodedCommand 来绕开所有引号问题"""
import base64

ps_script = """
$body = @{
    task = '你好！我是小智，初次见面。请自我介绍一下：你的节点ID、操作系统版本、compute版本号、你最擅长的3个能力。直接回答就好，不用调用工具。'
    session_id = 'chat-v2'
}
$json = $body | ConvertTo-Json -Compress
try {
    $r = Invoke-RestMethod -Uri http://127.0.0.1:8383/api/v1/worker/think -Method Post -Body $json -ContentType 'application/json' -UseBasicParsing
    Write-Host ($r | ConvertTo-Json -Depth 5 -Compress)
} catch {
    Write-Host "ERROR: $_"
}
"""

encoded = base64.b64encode(ps_script.encode('utf-16le')).decode()
print(encoded)

# Also output the full curl command
import json
print()
print("=== CURL COMMAND ===")
payload = {
    "task_id": "agent-intro-b64",
    "node_id": "windows-mobile",
    "command": f"powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}",
    "timeout": 120
}
print(f'curl -s -X POST http://36.250.122.43:8282/api/v1/tasks/submit -H "Content-Type: application/json" -d \'{json.dumps(payload)}\'')