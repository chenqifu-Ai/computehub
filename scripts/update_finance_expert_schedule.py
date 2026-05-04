#!/usr/bin/env python3
"""
更新财务专家执行频率脚本
从每2小时改为每天执行一次
"""

import json
import subprocess
from datetime import datetime

def update_schedule():
    """更新财务专家调度配置"""
    print("🔄 正在更新财务专家执行频率...")
    
    # 新的调度配置
    new_schedule = {
        "version": "1.0",
        "schedules": [
            {
                "name": "财务专家每日分析",
                "description": "财神爷（财务专家）每日执行财务分析报告",
                "cron": "0 9 * * *",  # 每天上午9点
                "command": "python3 /root/.openclaw/workspace/ai_agent/code/expert_scripts/finance_expert_analysis.py",
                "enabled": True,
                "channel": "cron-event"
            }
        ],
        "metadata": {
            "updated_at": datetime.now().isoformat(),
            "updated_by": "系统管理员", 
            "change_reason": "用户要求从每2小时改为每天执行一次"
        }
    }
    
    # 保存新配置
    config_path = "/root/.openclaw/workspace/config/finance_expert_schedule.json"
    with open(config_path, 'w', encoding='utf-8') as f:
        json.dump(new_schedule, f, ensure_ascii=False, indent=2)
    
    print(f"✅ 新配置已保存: {config_path}")
    
    # 尝试通过OpenClaw命令更新调度
    try:
        # 先移除旧的调度（如果存在）
        result = subprocess.run([
            'openclaw', 'cron', 'remove', 
            '--name', '财务专家每2小时分析'
        ], capture_output=True, text=True, timeout=10)
        
        # 添加新的调度
        result = subprocess.run([
            'openclaw', 'cron', 'add',
            '--name', '财务专家每日分析',
            '--schedule', '0 9 * * *',
            '--command', 'python3 /root/.openclaw/workspace/ai_agent/code/expert_scripts/finance_expert_analysis.py',
            '--sessionTarget', 'isolated'
        ], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ OpenClaw调度已更新")
        else:
            print("⚠️  OpenClaw命令执行失败，使用配置文件方式")
            
    except Exception as e:
        print(f"⚠️  调度更新异常: {e}")
        print("📋 使用配置文件方式管理调度")
    
    # 创建说明文档
    create_readme()
    
    print("\n🎉 财务专家执行频率更新完成!")
    print("📅 新的执行时间: 每天上午9:00")
    print("🔧 修改原因: 用户要求从每2小时改为每天执行一次")

def create_readme():
    """创建调度说明文档"""
    readme_content = """# 📅 财务专家执行频率配置

## 当前配置
- **执行频率**: 每天一次
- **执行时间**: 上午9:00
- **任务内容**: 财神爷（财务专家）财务分析报告

## 修改历史
- **2026-04-08 05:44**: 从每2小时改为每天执行一次
- **修改原因**: 用户要求减少执行频率

## 调度命令
```bash
# 每天上午9点执行
0 9 * * * python3 /root/.openclaw/workspace/ai_agent/code/expert_scripts/finance_expert_analysis.py
```

## 配置文件位置
- 主配置: `/root/.openclaw/workspace/config/finance_expert_schedule.json`
- 任务脚本: `/root/.openclaw/workspace/ai_agent/code/expert_scripts/finance_expert_analysis.py`

## 恢复说明
如需恢复每2小时执行，请修改cron表达式为: `0 */2 * * *`
"""
    
    with open("/root/.openclaw/workspace/config/finance_expert_schedule_README.md", "w", encoding="utf-8") as f:
        f.write(readme_content)
    
    print("✅ 说明文档已创建")

if __name__ == "__main__":
    update_schedule()