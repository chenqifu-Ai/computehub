#!/usr/bin/env python3
"""Delete stale scheduled tasks via PS EncodedCommand to avoid cmd escaping"""
import json, urllib.request, base64

ps_code = r'''
schtasks /delete /tn "\CHStart" /f
if ($LASTEXITCODE -eq 0) { Write-Host OK_CHStart } else { Write-Host FAIL_CHStart }
schtasks /delete /tn "\CHLogon" /f
if ($LASTEXITCODE -eq 0) { Write-Host OK_CHLogon } else { Write-Host FAIL_CHLogon }
schtasks /delete /tn "\ComputeHubStart" /f
if ($LASTEXITCODE -eq 0) { Write-Host OK_ComputeHubStart } else { Write-Host FAIL_ComputeHubStart }
schtasks /delete /tn "\ComputeHubLogon" /f
if ($LASTEXITCODE -eq 0) { Write-Host OK_ComputeHubLogon } else { Write-Host FAIL_ComputeHubLogon }
schtasks /delete /tn "\computehub-upgrade" /f
if ($LASTEXITCODE -eq 0) { Write-Host OK_computehub-upgrade } else { Write-Host FAIL_computehub-upgrade }
'''

encoded = base64.b64encode(ps_code.encode('utf-16-le')).decode()

task = {
    'node_id': 'Windows-mobile',
    'command': f'powershell -EncodedCommand {encoded}',
    'timeout': 20,
    'priority': 10,
    'max_retries': 1
}

req = urllib.request.Request(
    'http://36.250.122.43:8282/api/v1/tasks/submit',
    data=json.dumps(task).encode(),
    headers={'Content-Type': 'application/json'}
)
result = json.loads(urllib.request.urlopen(req, timeout=15).read())
print(json.dumps(result, indent=2, ensure_ascii=False))
