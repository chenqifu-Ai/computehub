#!/usr/bin/env python3

from scripts.email_utils import load_config
# -*- coding: utf-8 -*-
"""
系统性遗忘问题分析脚本
"""

import os
import json
import datetime
from pathlib import Path

def analyze_memory_system():
    """分析记忆系统问题"""
    analysis = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "issues": [],
        "root_causes": [],
        "solutions": []
    }
    
    # 1. 检查记忆文件结构
    memory_dir = Path("/root/.openclaw/workspace/memory")
    if memory_dir.exists():
        daily_files = list(memory_dir.glob("daily-ideas-*.md"))
        analysis["daily_files_count"] = len(daily_files)
        analysis["daily_files"] = [f.name for f in daily_files]
    else:
        analysis["issues"].append("memory目录不存在或路径错误")
    
    # 2. 检查MEMORY.md更新频率
    memory_file = Path("/root/.openclaw/workspace/MEMORY.md")
    if memory_file.exists():
        stat = memory_file.stat()
        last_modified = datetime.datetime.fromtimestamp(stat.st_mtime)
        now = datetime.datetime.now()
        hours_since_update = (now - last_modified).total_seconds() / 3600
        
        analysis["memory_last_updated"] = last_modified.strftime("%Y-%m-%d %H:%M:%S")
        analysis["hours_since_update"] = round(hours_since_update, 2)
        
        if hours_since_update > 24:
            analysis["issues"].append(f"MEMORY.md超过{int(hours_since_update/24)}天未更新")
    
    # 3. 检查HEARTBEAT机制
    heartbeat_file = Path("/root/.openclaw/workspace/HEARTBEAT.md")
    if heartbeat_file.exists():
        with open(heartbeat_file, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # 检查心跳机制是否有效
        if "检查文件" in content and "daily-ideas" in content:
            analysis["heartbeat_configured"] = True
        else:
            analysis["issues"].append("HEARTBEAT.md配置不完整")
            analysis["heartbeat_configured"] = False
    
    # 4. 分析可能的问题根源
    analysis["root_causes"] = [
        "AI会话重启导致记忆丢失（每次都是新会话）",
        "记忆文件未及时更新或整合",
        "没有强制性的记忆更新机制",
        "信息分散在多个文件中，缺乏集中管理",
        "依赖用户提醒而不是主动记忆"
    ]
    
    # 5. 提出解决方案
    analysis["solutions"] = [
        {
            "name": "强制记忆更新机制",
            "description": "每次会话启动时强制更新MEMORY.md",
            "priority": "高"
        },
        {
            "name": "智能记忆整合系统",
            "description": "自动从daily文件中提取重要信息到MEMORY.md",
            "priority": "高"
        },
        {
            "name": "记忆检查点",
            "description": "设置关键信息检查点，确保重要信息被记住",
            "priority": "中"
        },
        {
            "name": "配置信息数据库",
            "description": "创建专门的配置文件数据库，避免遗忘关键配置",
            "priority": "高"
        }
    ]
    
    return analysis

def create_memory_checkpoint():
    """创建记忆检查点"""
    checkpoint = {
        "timestamp": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "critical_info": {
            "emails": [
                {
                    "email": "19525456@qq.com",
                    "auth_code": "__USE_CONFIG__",
                    "type": "qq",
                    "config_file": "/root/.openclaw/workspace/config/email.conf"
                },
                {
                    "email": "chenqifu_fzu@163.com",
                    "auth_code": "AWZBPidhza74EbV8",
                    "type": "163",
                    "config_file": "/root/.openclaw/workspace/config/163_email.conf"
                }
            ],
            "api_keys": {
                "ali_bailian": "sk-65ca99f6fd55437fba47dc7ba7973242",
                "ollama_cloud": "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"
            },
            "stock_positions": {
                "hualian": {
                    "code": "000882",
                    "shares": 22600,
                    "cost_price": 1.779
                }
            }
        }
    }
    
    checkpoint_file = "/root/.openclaw/workspace/ai_agent/results/memory_checkpoint.json"
    os.makedirs(os.path.dirname(checkpoint_file), exist_ok=True)
    
    with open(checkpoint_file, 'w', encoding='utf-8') as f:
        json.dump(checkpoint, f, ensure_ascii=False, indent=2)
    
    return checkpoint

def main():
    print("开始分析系统性遗忘问题...\n")
    
    # 分析系统
    analysis = analyze_memory_system()
    
    # 创建记忆检查点
    checkpoint = create_memory_checkpoint()
    
    # 保存分析结果
    result_file = "/root/.openclaw/workspace/ai_agent/results/memory_analysis.json"
    os.makedirs(os.path.dirname(result_file), exist_ok=True)
    
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({"analysis": analysis, "checkpoint": checkpoint}, f, ensure_ascii=False, indent=2)
    
    print("分析完成!")
    print(f"发现 {len(analysis['issues'])} 个问题")
    print(f"识别 {len(analysis['root_causes'])} 个根本原因")
    print(f"提出 {len(analysis['solutions'])} 个解决方案")
    print("\n记忆检查点已创建，包含关键信息")

if __name__ == "__main__":
    main()
# 从统一配置加载
_cfg = load_config()
AUTH_CODE = _cfg["auth_code"]
