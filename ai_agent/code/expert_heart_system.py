#!/usr/bin/env python3
"""
💓 专家心脏系统 - 让专家真正动起来！
"""

import json
import time
from pathlib import Path
from datetime import datetime

class ExpertHeart:
    def __init__(self, expert_name, expert_id):
        self.name = expert_name
        self.id = expert_id
        self.heart_file = Path(f"/root/.openclaw/workspace/skills/{expert_id}/heart.json")
        self.heart_file.parent.mkdir(parents=True, exist_ok=True)
        
    def install_heart(self):
        """安装心脏"""
        heart_data = {
            "expert": self.name,
            "heart_installed": datetime.now().isoformat(),
            "heartbeat": "strong",
            "motivation": "high",
            "kpi": {
                "daily_output": 0,
                "quality_score": 0,
                "deadline_met": False
            },
            "last_heartbeat": datetime.now().isoformat(),
            "status": "active"
        }
        
        with open(self.heart_file, 'w', encoding='utf-8') as f:
            json.dump(heart_data, f, ensure_ascii=False, indent=2)
        
        print(f"💓 已为 {self.name} 安装心脏！")
        return heart_data
    
    def check_heartbeat(self):
        """检查心跳"""
        if not self.heart_file.exists():
            print(f"❌ {self.name} 没有心脏！")
            return False
        
        with open(self.heart_file, 'r') as f:
            heart = json.load(f)
        
        # 检查是否在跳动
        last_beat = datetime.fromisoformat(heart['last_heartbeat'])
        time_diff = (datetime.now() - last_beat).total_seconds() / 60
        
        if time_diff > 60:  # 超过1小时没心跳
            print(f"💀 {self.name} 心脏停止跳动！")
            return False
        else:
            print(f"💓 {self.name} 心跳正常 ({time_diff:.1f}分钟前)")
            return True
    
    def force_heartbeat(self):
        """强制心跳"""
        if not self.heart_file.exists():
            self.install_heart()
        
        with open(self.heart_file, 'r') as f:
            heart = json.load(f)
        
        heart['last_heartbeat'] = datetime.now().isoformat()
        heart['motivation'] = "high"
        
        with open(self.heart_file, 'w', encoding='utf-8') as f:
            json.dump(heart, f, ensure_ascii=False, indent=2)
        
        print(f"⚡ 强制 {self.name} 心跳！")

# 为所有专家安装心脏
experts = [
    ('码神', 'network-expert'),
    ('销冠王', 'marketing-expert'),
    ('金算子', 'finance-expert'),
    ('财神爷', 'finance-advisor'),
    ('人精', 'hr-expert'),
    ('法海', 'legal-advisor'),
    ('智多星', 'ceo-advisor')
]

print("🔧 正在为专家安装心脏...")
print("-"*70)

for name, expert_id in experts:
    heart = ExpertHeart(name, expert_id)
    heart.install_heart()

print("-"*70)
print("✅ 所有专家心脏已安装！")
print("")

# 检查心跳
print("🔍 检查专家心跳...")
print("-"*70)

for name, expert_id in experts:
    heart = ExpertHeart(name, expert_id)
    heart.check_heartbeat()

print("-"*70)
print("💓 专家心脏系统安装完成！")
