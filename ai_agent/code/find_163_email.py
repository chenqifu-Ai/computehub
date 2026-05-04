#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查找163邮箱配置信息脚本
"""

import os
import json
import glob

def search_163_email_configs():
    """搜索系统中可能存在的163邮箱配置"""
    configs = {}
    
    # 搜索可能的配置文件位置
    search_paths = [
        "/root/.openclaw/workspace/config/",
        "/root/.openclaw/workspace/",
        "/root/.openclaw/",
        "~/.openclaw/workspace/config/",
        "~/.openclaw/workspace/"
    ]
    
    found_files = []
    for base_path in search_paths:
        expanded_path = os.path.expanduser(base_path)
        if os.path.exists(expanded_path):
            # 查找包含email、mail、163等关键词的文件
            patterns = ["*email*", "*mail*", "*163*", "*.conf", "*.cfg", "*.ini"]
            for pattern in patterns:
                matches = glob.glob(os.path.join(expanded_path, pattern))
                for match in matches:
                    if os.path.isfile(match):
                        # 检查文件内容是否包含163邮箱相关信息
                        try:
                            with open(match, 'r', encoding='utf-8', errors='ignore') as f:
                                content = f.read().lower()
                                if '163.com' in content or '163' in content:
                                    found_files.append(match)
                                    # 尝试解析配置
                                    config_data = parse_config_file(match)
                                    if config_data:
                                        configs[f"163_config_{len(configs)+1}"] = {
                                            "file_path": match,
                                            "config": config_data
                                        }
                        except Exception as e:
                            continue
    
    # 也检查MEMORY.md中是否有163邮箱信息
    memory_file = "/root/.openclaw/workspace/MEMORY.md"
    if os.path.exists(memory_file):
        with open(memory_file, 'r', encoding='utf-8') as f:
            content = f.read()
            if '163.com' in content:
                configs["memory_163_info"] = {
                    "source": "MEMORY.md",
                    "content_snippet": "Found 163.com reference in MEMORY.md"
                }
    
    return configs, found_files

def parse_config_file(file_path):
    """尝试解析配置文件"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            config = {}
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#'):
                    if '=' in line:
                        key, value = line.split('=', 1)
                        config[key.strip()] = value.strip()
                    elif '@163.com' in line:
                        # 可能是邮箱地址行
                        config['email_address'] = line
            return config if config else None
    except Exception:
        return None

def save_results(configs, found_files):
    """保存搜索结果"""
    result = {
        "configs": configs,
        "found_files": found_files,
        "search_timestamp": __import__('datetime').datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }
    
    result_file = "/root/.openclaw/workspace/ai_agent/results/163_email_search.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

def main():
    configs, found_files = search_163_email_configs()
    save_results(configs, found_files)
    
    print(f"搜索完成!")
    print(f"找到 {len(found_files)} 个可能相关的文件")
    print(f"解析出 {len(configs)} 个有效配置")

if __name__ == "__main__":
    main()