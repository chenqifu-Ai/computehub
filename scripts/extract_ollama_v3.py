#!/usr/bin/env python3
"""Write and run extraction script on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Write the script
r1 = cluster_exec('wanlida-work01', '''
$code = @'
import struct, os, zlib

f = 'C:\\Users\\admin\\AppData\\Local\\Temp\\OllamaSetup.exe'
outdir = 'C:\\Users\\admin\\ollama'

with open(f, 'rb') as fh:
    data = fh.read()

idx = data.find(b'7z\xbc\xaf\x27\x1c')
if idx >= 0:
    print('Found 7z archive at offset', idx)
    with open(os.path.join(outdir, 'ollama.7z'), 'wb') as out:
        out.write(data[idx:])
    print('Wrote', len(data)-idx, 'bytes to ollama.7z')
else:
    print('7z signature not found')
    idx2 = data.find(b'ollama.exe')
    print('ollama.exe string at:', idx2)
'@

$pyFile = "$env:TEMP\\extract_ollama2.py"
Set-Content -Path $pyFile -Value $code -Encoding UTF8
Write-Output "Script written"
''', timeout=15)
print("=== Write ===")
print(r1.get('stdout',''))
print("exit_code:", r1.get('exit_code',''))

# Run it
r2 = cluster_exec('wanlida-work01', 'python3 "$env:TEMP\\extract_ollama2.py" 2>&1', timeout=60)
print("\n=== Run ===")
print(r2.get('stdout',''))
print("exit_code:", r2.get('exit_code',''))
