#!/usr/bin/env python3
"""Check disk space and large directories on Windows-mobile"""
import json, urllib.request, base64

ps_code = r'''
Write-Host "=== DISK FREE SPACE ==="
Get-PSDrive -PSProvider FileSystem | Where-Object { $_.Used -gt 0 } | Select-Object Name, @{n="UsedGB";e={[math]::Round($_.Used/1GB,2)}}, @{n="FreeGB";e={[math]::Round($_.Free/1GB,2)}}, @{n="TotalGB";e={[math]::Round(($_.Used+$_.Free)/1GB,2)}}
Write-Host ""
Write-Host "=== TOP 20 BIGGEST FOLDERS (C:\, depth 1) ==="
Get-ChildItem -Path C:\ -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $size = (Get-ChildItem -Path $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    [PSCustomObject]@{
        Name = $_.Name
        SizeGB = [math]::Round(($size/1GB), 2)
    }
} | Sort-Object SizeGB -Descending | Select-Object -First 20 | Format-Table -AutoSize
Write-Host ""
Write-Host "=== BIG DIRECTORIES under C:\Users ==="
Get-ChildItem -Path C:\Users -Directory -ErrorAction SilentlyContinue | ForEach-Object {
    $size = (Get-ChildItem -Path $_.FullName -Recurse -File -ErrorAction SilentlyContinue | Measure-Object -Property Length -Sum).Sum
    [PSCustomObject]@{
        Name = $_.Name
        SizeGB = [math]::Round(($size/1GB), 2)
    }
} | Sort-Object SizeGB -Descending | Format-Table -AutoSize
'''

b64 = base64.b64encode(ps_code.encode('utf-16-le')).decode()

task = {
    'node_id': 'Windows-mobile',
    'command': f'powershell -EncodedCommand {b64}',
    'timeout': 60,
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
