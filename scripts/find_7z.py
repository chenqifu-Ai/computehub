#!/usr/bin/env python3
"""Find and extract 7z from OllamaSetup.exe on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$pyScript = @'
import struct, os, zlib

f = r'C:\Users\admin\AppData\Local\Temp\OllamaSetup.exe'
outdir = r'C:\Users\admin\ollama'

with open(f, 'rb') as fh:
    data = fh.read()

# Search for 7z signature
idx = data.find(b"7z\xbc\xaf\x27\x1c")
print(f"7z signature at offset: {idx}")

# Search for ollama.exe in raw data
idx2 = 0
count = 0
while True:
    idx2 = data.find(b"ollama.exe", idx2)
    if idx2 < 0:
        break
    print(f"ollama.exe at offset {idx2}: {data[idx2-10:idx2+20]}")
    idx2 += 1
    count += 1
    if count > 5:
        break

# Search for PK signature (zip)
idx3 = 0
while True:
    idx3 = data.find(b"PK\x03\x04", idx3)
    if idx3 < 0:
        break
    print(f"PK zip at offset {idx3}")
    idx3 += 1
    if idx3 > 1000000:
        break

# Check file size
print(f"File size: {len(data)} bytes")
'@

$pyFile = "$env:TEMP\\find_7z.py"
Set-Content -Path $pyFile -Value $pyScript -Encoding UTF8
python3 $pyFile 2>&1
''', timeout=60)
print("=== Find 7z ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
