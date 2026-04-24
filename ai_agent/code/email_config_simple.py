#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
简化版邮箱配置信息提取脚本
"""

import os
import json

def extract_email_config():
    """提取邮箱配置信息"""
    config = {}
    
    # 从MEMORY.md获取基本信息
    config["primary_email"] = {
        "email": "19525456@qq.com",
        "auth_code": "xunlwhjokescbgdd",
        "imap_server": "imap.qq.com",
        "imap_port": 993,
        "smtp_server": "smtp.qq.com", 
        "smtp_port": 465,
        "config_file": "~/.openclaw/workspace/config/email.conf"
    }
    
    # 从配置文件读取详细信息
    email_conf_path = "/root/.openclaw/workspace/config/email.conf"
    if os.path.exists(email_conf_path):
        with open(email_conf_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            file_config = {}
            for line in lines:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    file_config[key] = value
            
            config["config_file_details"] = file_config
    
    return config

def save_config(config):
    """保存配置到结果文件"""
    result_file = "/root/.openclaw/workspace/ai_agent/results/email_configs.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)

def main():
    config = extract_email_config()
    save_config(config)
    print("邮箱配置提取完成!")

if __name__ == "__main__":
    main()