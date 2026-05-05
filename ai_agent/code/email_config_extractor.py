#!/usr/bin/env python3

from scripts.email_utils import load_config
# -*- coding: utf-8 -*-
"""
邮箱配置信息提取脚本
"""

import os
import json
import configparser

def extract_email_configs():
    """提取邮箱配置信息"""
    configs = {}
    
    # 从MEMORY.md中提取已知的邮箱配置
    memory_file = "/root/.openclaw/workspace/MEMORY.md"
    if os.path.exists(memory_file):
        with open(memory_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
            # 提取QQ邮箱配置
            if "邮件API配置" in content:
                email_config = {
                    "email": "19525456@qq.com",
                    "auth_code": "__USE_CONFIG__",
                    "imap_server": "imap.qq.com:993",
                    "smtp_server": "smtp.qq.com:465",
                    "config_file": "~/.openclaw/workspace/config/email.conf"
                }
                configs["qq_email"] = email_config
    
    # 检查email.conf配置文件
    email_conf_path = "/root/.openclaw/workspace/config/email.conf"
    if os.path.exists(os.path.expanduser(email_conf_path)):
        config = configparser.ConfigParser()
        config.read(os.path.expanduser(email_conf_path))
        if 'email' in config:
            file_config = dict(config['email'])
            configs["email_conf_file"] = file_config
    
    return configs

def save_configs(configs):
    """保存配置到结果文件"""
    result_file = "/root/.openclaw/workspace/ai_agent/results/email_configs.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(configs, f, ensure_ascii=False, indent=2)

def main():
    configs = extract_email_configs()
    save_configs(configs)
    print(f"找到 {len(configs)} 个邮箱配置")
    for name in configs:
        print(f"- {name}")

if __name__ == "__main__":
    main()
# 从统一配置加载
_cfg = load_config()
AUTH_CODE = _cfg["auth_code"]
