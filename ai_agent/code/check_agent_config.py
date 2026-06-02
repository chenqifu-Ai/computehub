#!/usr/bin/env python3
"""Check what LLM config the Windows Agent is using"""
import base64, json, urllib.request, time, sys

ps_script = """
try {
    Write-Host "=== config.json ==="
    Get-Content C:\\tmp\\computehub\\agent_config.json -ErrorAction Stop -Raw
} catch { Write-Host "NOT FOUND at C:\\tmp\\computehub\\" }
try {
    Write-Host "=== config.json (current dir) ==="
    $pwd = (Get-Location).Path
    Get-Content "$pwd\\agent_config.json" -Raw
} catch { Write-Host "NOT FOUND at current dir: $(Get-Location)" }
try {
    Write-Host "=== config near computehub ==="
    $p = (Get-Process computehub -ErrorAction Stop | Select-Object -First 1).Path
    $d = Split-Path $p
    Get-Content (Join-Path $d "config.json") -Raw
} catch { Write-Host "NOT FOUND near computehub.exe" }
try {
    Write-Host "=== computehub version ==="
    computehub version
} catch { Write-Host "version command failed" }
"""

encoded = base64.b64encode(ps_script.encode('utf-16le')).decode()
payload = json.dumps({
    "task_id": "check-agent-config-v2",
    "node_id": "windows-mobile",
    "command": f"powershell -NoProfile -ExecutionPolicy Bypass -EncodedCommand {encoded}",
    "timeout": 30
})

req = urllib.request.Request(
    "http://36.250.122.43:8282/api/v1/tasks/submit",
    data=payload.encode(),
    headers={"Content-Type": "application/json"},
    method="POST"
)
resp = urllib.request.urlopen(req)
print(f"submit: {json.loads(resp.read())}", file=sys.stderr)

for i in range(15):
    time.sleep(2)
    try:
        detail_url = f"http://36.250.122.43:8282/api/v1/tasks/detail?task_id=check-agent-config-v2&node_id=windows-mobile"
        detail_resp = urllib.request.urlopen(detail_url, timeout=5)
        detail = json.loads(detail_resp.read())
        data = detail.get("data", {})
        if data.get("status") == "completed":
            print(data.get("stdout", ""))
            sys.exit(0)
        print(f"  [{i*2}s] {data.get('status')}", file=sys.stderr)
    except Exception as e:
        print(f"  [{i*2}s] {e}", file=sys.stderr)

print("timeout")
sys.exit(1)