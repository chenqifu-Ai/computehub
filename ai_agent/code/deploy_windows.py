#!/usr/bin/env python3
"""Deploy computehub-worker to Windows-mobile via Gateway task submit API"""
import json, urllib.request

gw = "http://36.250.122.43:8282"

# PowerShell script to download + start new worker
ps_script = r'''
$url = "http://36.250.122.43:8282/api/v1/download?file=computehub-worker-win-amd64.exe"
$out = "C:\Users\xiaomi\computehub-worker.exe"
Write-Host "📥 Downloading new computehub-worker..."
Invoke-WebRequest -Uri $url -OutFile $out
$size = (Get-Item $out).Length / 1MB
Write-Host ("✅ Downloaded: {0:F1} MB" -f $size)
Write-Host "🚀 Starting new worker with --agent..."
# Kill old worker if running
Get-Process -Name "computehub-worker" -ErrorAction SilentlyContinue | Stop-Process -Force
Start-Process -NoNewWindow -FilePath $out -ArgumentList "--gw http://36.250.122.43:8282 --node-id Windows-mobile --agent"
Write-Host "✅ Worker started"
'''

task = {
    "node_id": "Windows-mobile",
    "command": f'powershell.exe -Command "{ps_script.strip()}"'
}

req = urllib.request.Request(
    f"{gw}/api/v1/tasks/submit",
    data=json.dumps(task).encode(),
    headers={"Content-Type": "application/json"}
)

try:
    with urllib.request.urlopen(req, timeout=30) as r:
        print("Response:", r.read().decode())
except Exception as e:
    print(f"Error: {e}")