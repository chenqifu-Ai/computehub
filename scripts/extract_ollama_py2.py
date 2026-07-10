#!/usr/bin/env python3
"""Extract ollama.exe from OllamaSetup using Python on the node"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Write Python script to node first
r1 = cluster_exec('wanlida-work01', '''
$pyScript = @"
import struct, os, zlib

f = 'C:\\Users\\admin\\AppData\\Local\\Temp\\OllamaSetup.exe'
outdir = 'C:\\Users\\admin\\ollama'

with open(f, 'rb') as fh:
    data = fh.read()

idx = data.find(b'7z\\xbc\\xaf\\x27\\x1c')
if idx >= 0:
    print(f'Found 7z archive at offset {idx}')
    with open(os.path.join(outdir, 'ollama.7z'), 'wb') as out:
        out.write(data[idx:])
    print(f'Wrote {len(data)-idx} bytes to ollama.7z')
else:
    print('7z signature not found')
    idx2 = data.find(b'ollama.exe')
    print(f'ollama.exe string at: {idx2}')
"@

$pyFile = "$env:TEMP\\extract_ollama.py"
Set-Content -Path $pyFile -Value $pyScript -Encoding UTF8
Write-Output "Script written to $pyFile"
''', timeout=15)
print("=== Write script ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))
