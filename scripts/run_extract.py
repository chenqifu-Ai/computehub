#!/usr/bin/env python3
"""Run the extraction script on wanlida-work01"""
import sys
sys.path.insert(0, '/home/computehub/ComputeHub')
from scripts.cluster_exec import cluster_exec

r = cluster_exec('wanlida-work01', 'python3 "$env:TEMP\\extract_ollama.py" 2>&1', timeout=60)
print("=== Run extract ===")
print(r.get('stdout',''))
print("exit_code:", r.get('exit_code',''))
