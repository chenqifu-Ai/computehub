#!/usr/bin/env python3
"""Find 7z archive in OllamaSetup.exe"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Write Python script to node
r1 = cluster_exec('wanlida-work01', '''
$code = 'import struct, os, zlib
f = "C:\\\\Users\\\\admin\\\\AppData\\\\Local\\\\Temp\\\\OllamaSetup.exe"
outdir = "C:\\\\Users\\\\admin\\\\ollama"
with open(f, "rb") as fh:
    data = fh.read()
idx = data.find(b"7z\\xbc\\xaf\\x27\\x1c")
print("7z signature at offset:", idx)
idx2 = data.find(b"PK\\x03\\x04")
print("PK zip at offset:", idx2)
print("File size:", len(data))
'
$pyFile = "$env:TEMP\\find_7z2.py"
Set-Content -Path $pyFile -Value $code -Encoding UTF8
Write-Output "Written"
''', timeout=15)
print("=== Write ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))

# Run it
r2 = cluster_exec('wanlida-work01', 'python3 "$env:TEMP\\find_7z2.py" 2>&1', timeout=30)
print("\n=== Run ===")
print(r2.get('stdout',''))
print("exit_code:", r2.get('exit_code',''))
