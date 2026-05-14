#!/usr/bin/env python3
"""打包 ComputeHub v0.7.6 工程源码（排除二进制/日志/大文件）"""

import os
import subprocess
import tarfile

PROJECT_DIR = "/root/.openclaw/workspace/projects/computehub"
OUTPUT_DIR = "/root/.openclaw/workspace/ai_agent/results"
OUTPUT_FILE = os.path.join(OUTPUT_DIR, "computehub-v0.7.6.tar.gz")

def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    
    print("📦 打包 ComputeHub v0.7.6（源码）...")
    print(f"   项目大小: {subprocess.run(['du', '-sh', PROJECT_DIR], capture_output=True, text=True).stdout.strip()}")
    
    with tarfile.open(OUTPUT_FILE, "w:gz") as tar:
        # 排除大文件
        for root, dirs, files in os.walk(PROJECT_DIR):
            # 跳过大目录
            rel = os.path.relpath(root, PROJECT_DIR)
            if rel in ('bin', 'deploy', 'test-results') or rel.startswith(('bin/', 'deploy/', 'test-results/')):
                dirs.clear()
                continue
            
            for f in files:
                if any(f.endswith(ext) for ext in ['.log', '.bak', '.bak.*', '.tar.gz', '.tmp']):
                    continue
                # 跳过二进制文件
                if f in ('gateway', 'worker', 'tui'):
                    continue
                full = os.path.join(root, f)
                arcname = os.path.relpath(full, PROJECT_DIR)
                tar.add(full, arcname=arcname)
    
    size_mb = os.path.getsize(OUTPUT_FILE) / 1024 / 1024
    print(f"✅ 打包完成: {OUTPUT_FILE}")
    print(f"   大小: {size_mb:.1f}MB")
    
    # 列出包内容
    result = subprocess.run(f"tar -tzf {OUTPUT_FILE} | wc -l", shell=True, capture_output=True, text=True)
    print(f"   文件数: {result.stdout.strip()}")
    
    print("\n📁 目录结构:")
    result = subprocess.run(f"tar -tzf {OUTPUT_FILE} | head -50", shell=True, capture_output=True, text=True)
    for line in result.stdout.strip().split('\n'):
        depth = line.count('/')
        print(f"{'  ' * depth}{os.path.basename(line) if '/' in line else line}")

if __name__ == '__main__':
    main()
