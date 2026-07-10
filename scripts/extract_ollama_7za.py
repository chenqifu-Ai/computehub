#!/usr/bin/env python3
"""Extract ollama.exe from OllamaSetup using 7za on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$7za = "$env:TEMP\\7za_$(Get-Random).exe"
# Find the 7za we downloaded
$7zaFiles = Get-ChildItem "$env:TEMP\\7za_*.exe" -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending
$7za = $7zaFiles[0].FullName
Write-Output "Using 7za: $7za"

$installer = "C:\\Users\\admin\\AppData\\Local\\Temp\\OllamaSetup.exe"
$outDir = "$env:TEMP\\ollama_extracted_$(Get-Random)"

New-Item -ItemType Directory -Path $outDir -Force | Out-Null

Write-Output "=== Extracting with 7za ==="
$result = & $7za x $installer -o"$outDir" -y 2>&1
Write-Output $result

Write-Output "=== Files extracted ==="
Get-ChildItem -Path $outDir -Recurse | Select-Object Name,Length | Format-Table -AutoSize

# Find ollama.exe
$ollamaExe = Get-ChildItem -Path $outDir -Recurse -Filter "ollama.exe" -ErrorAction SilentlyContinue
if ($ollamaExe) {
    Write-Output "Found ollama.exe at: $($ollamaExe.FullName)"
    Write-Output "Size: $($ollamaExe.Length) bytes"
    # Copy to ollama dir
    Copy-Item $ollamaExe.FullName "$env:USERPROFILE\\ollama\\ollama_new.exe" -Force
    Write-Output "Copied to ollama dir"
} else {
    Write-Output "ollama.exe not found in extracted files"
}
''', timeout=120)
print("=== Extract ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
