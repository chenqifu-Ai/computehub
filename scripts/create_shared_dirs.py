#!/usr/bin/env python3
"""
Phase 0: 创建共享目录结构
三智共享知识库基础目录
"""
import os
import sys

BASE_DIR = os.environ.get('GALAXY_SHARED_DIR', '/home/computehub/.openclaw/workspace/shared')

DIRS = [
    'knowledge',      # 通用经验库
    'patterns',       # 发现的模式
    'insights',       # 提炼的洞察
    'timeline',       # 事件时间线
    'galaxy',         # 银河计划专用
]

def main():
    created = 0
    for d in DIRS:
        path = os.path.join(BASE_DIR, d)
        if not os.path.exists(path):
            os.makedirs(path)
            created += 1
            print(f'  ✅ 创建: {path}')
        else:
            print(f'  ⏭️  已存在: {path}')
    
    print(f'\n总计: {created} 个目录创建, 共享目录根目录: {BASE_DIR}')
    return 0

if __name__ == '__main__':
    sys.exit(main())
