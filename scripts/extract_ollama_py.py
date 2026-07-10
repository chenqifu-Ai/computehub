#!/usr/bin/env python3
"""Extract ollama.exe from OllamaSetup using Python on the node"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', '''
$installer = "C:\\Users\\admin\\AppData\\Local\\Temp\\OllamaSetup.exe"
$ollamaDir = "$env:USERPROFILE\\ollama"

Write-Output "=== Try to extract with Python ==="
$pyScript = @"
import struct, os, zlib

f = r'$installer'
outdir = r'$ollamaDir'

with open(f, 'rb') as fh:
    data = fh.read()

# Search for 7z signature in the file
idx = data.find(b'7z\xbc\xaf\x27\x1c')
if idx >= 0:
    print(f'Found 7z archive at offset {idx}')
    # Write 7z to temp file
    with open(os.path.join(outdir, 'ollama.7z'), 'wb') as out:
        out.write(data[idx:])
    print(f'Wrote {len(data)-idx} bytes to ollama.7z')
else:
    print('7z signature not found')
    # Try to find ollama.exe in the raw data
    idx2 = data.find(b'ollama.exe')
    print(f'ollama.exe string at: {idx2}')
"@

# Write Python script to node
$pyFile = "$env:TEMP\\extract_ollama.py"
Set-Content -Path $pyFile -Value $pyScript -Encoding UTF8

# Run it
$result = python3 $pyFile 2>&1
Write-Output $result
''', timeout=60)
print("=== Python extract ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
