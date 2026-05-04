#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
创建163邮箱配置脚本
"""

import os
import json
from datetime import datetime

def create_163_email_config():
    """创建163邮箱配置"""
    config = {
        "email": "chenqifu_fzu@163.com",
        "auth_code": "AWZBPidhza74EbV8",
        "imap_server": "imap.163.com",
        "imap_port": 993,
        "smtp_server": "smtp.163.com",
        "smtp_port": 465,
        "config_file": "~/.openclaw/workspace/config/163_email.conf"
    }
    
    # 创建配置文件
    config_content = """# 163邮箱配置 - chenqifu_fzu@163.com
IMAP_SERVER=imap.163.com
IMAP_PORT=993
SMTP_SERVER=smtp.163.com
SMTP_PORT=465
EMAIL=chenqifu_fzu@163.com
AUTH_CODE=AWZBPidhza74EbV8

# 注意：授权码是敏感信息，请勿泄露
"""
    
    config_file_path = "/root/.openclaw/workspace/config/163_email.conf"
    os.makedirs(os.path.dirname(config_file_path), exist_ok=True)
    
    with open(config_file_path, 'w', encoding='utf-8') as f:
        f.write(config_content)
    
    return config

def update_memory_with_163_email():
    """更新MEMORY.md文件，添加163邮箱信息"""
    memory_file = "/root/.openclaw/workspace/MEMORY.md"
    
    if os.path.exists(memory_file):
        with open(memory_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 检查是否已有163邮箱配置
        if "163邮箱配置" not in content:
            # 在邮件API配置部分后添加163邮箱配置
            if "邮件API配置" in content:
                # 找到邮件API配置部分结束的位置
                sections = content.split("## ")
                new_content = ""
                
                for i, section in enumerate(sections):
                    new_content += "## " + section if i > 0 else section
                    
                    if "邮件API配置" in section and i < len(sections) - 1:
                        # 在邮件API配置后添加163邮箱配置
                        new_content += "\n\n### 163邮箱配置\n"
                        new_content += "- 邮箱：chenqifu_fzu@163.com\n"
                        new_content += "- 授权码：AWZBPidhza74EbV8\n"
                        new_content += "- IMAP：imap.163.com:993\n"
                        new_content += "- SMTP：smtp.163.com:465\n"
                        new_content += "- 配置文件：~/.openclaw/workspace/config/163_email.conf\n"
                
                # 更新文件
                with open(memory_file, 'w', encoding='utf-8') as f:
                    f.write(new_content)

def save_config_info(config):
    """保存配置信息到结果文件"""
    result = {
        "163_email_config": config,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "status": "配置创建成功"
    }
    
    result_file = "/root/.openclaw/workspace/ai_agent/results/163_email_config_result.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

def main():
    config = create_163_email_config()
    update_memory_with_163_email()
    save_config_info(config)
    print("163邮箱配置创建完成!")

if __name__ == "__main__":
    main()