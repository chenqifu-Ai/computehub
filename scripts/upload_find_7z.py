#!/usr/bin/env python3
"""Find 7z in OllamaSetup.exe - write script to node properly"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

# Write the Python script to a file on ECS first, then upload via Gallery
script_content = '''import struct, os, zlib
f = "C:\\\\Users\\\\admin\\\\AppData\\\\Local\\\\Temp\\\\OllamaSetup.exe"
outdir = "C:\\\\Users\\\\admin\\\\ollama"
with open(f, "rb") as fh:
    data = fh.read()
idx = data.find(b"7z\\\\xbc\\\\xaf\\\\x27\\\\x1c")
print("7z signature at offset:", idx)
idx2 = data.find(b"PK\\\\x03\\\\x04")
print("PK zip at offset:", idx2)
print("File size:", len(data))
'''

# Write to a temp file on ECS
with open('/tmp/find_7z_script.py', 'w') as f:
    f.write(script_content)

# Upload to Gallery
import shutil
shutil.copy('/tmp/find_7z_script.py', '/home/computehub/gallery/find_7z_script.py')

print("Script uploaded to Gallery")
