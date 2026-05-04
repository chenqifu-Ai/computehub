#!/usr/bin/env python3
"""
🎁 专家福利系统 - 激励专家好好干活！
"""

import json
from pathlib import Path
from datetime import datetime

class ExpertWelfare:
    def __init__(self, expert_name, expert_id):
        self.name = expert_name
        self.id = expert_id
        self.welfare_file = Path(f"/root/.openclaw/workspace/skills/{expert_id}/welfare.json")
        self.welfare_file.parent.mkdir(parents=True, exist_ok=True)
        
    def setup_welfare(self):
        """设置福利"""
        welfare_data = {
            "expert": self.name,
            "welfare_setup": datetime.now().isoformat(),
            "daily_benefits": {
                "morning_coffee": True,
                "lunch_break": "12:00-13:00",
                "afternoon_snack": "15:00",
                "evening_rest": "18:00-19:00"
            },
            "weekly_rewards": {
                "monday_motivation": "周一激励红包",
                "friday_reward": "周五完成奖励",
                "weekend_rest": "周末双休"
            },
            "performance_bonus": {
                "daily_output_bonus": "产出达标奖励",
                "quality_bonus": "质量优秀奖励",
                "innovation_bonus": "创新贡献奖励"
            },
            "last_reward": None,
            "next_reward": datetime.now().replace(hour=18, minute=0, second=0).isoformat()
        }
        
        with open(self.welfare_file, 'w', encoding='utf-8') as f:
            json.dump(welfare_data, f, ensure_ascii=False, indent=2)
        
        print(f"🎁 已为 {self.name} 设置福利！")
        return welfare_data
    
    def give_reward(self, reward_type):
        """发放奖励"""
        if not self.welfare_file.exists():
            self.setup_welfare()
        
        with open(self.welfare_file, 'r') as f:
            welfare = json.load(f)
        
        welfare['last_reward'] = {
            "type": reward_type,
            "time": datetime.now().isoformat(),
            "amount": "待定"
        }
        
        with open(self.welfare_file, 'w', encoding='utf-8') as f:
            json.dump(welfare, f, ensure_ascii=False, indent=2)
        
        print(f"🎉 给 {self.name} 发放 {reward_type} 奖励！")

# 为所有专家设置福利
experts = [
    ('码神', 'network-expert'),
    ('销冠王', 'marketing-expert'),
    ('金算子', 'finance-expert'),
    ('财神爷', 'finance-advisor'),
    ('人精', 'hr-expert'),
    ('法海', 'legal-advisor'),
    ('智多星', 'ceo-advisor')
]

print("🎁 正在为专家设置福利...")
print("-"*70)

for name, expert_id in experts:
    welfare = ExpertWelfare(name, expert_id)
    welfare.setup_welfare()

print("-"*70)
print("✅ 所有专家福利已设置！")
print("")

# 立即发放今日福利
print("🎉 立即发放今日福利...")
print("-"*70)

for name, expert_id in experts:
    welfare = ExpertWelfare(name, expert_id)
    welfare.give_reward("周一激励红包")

print("-"*70)
print("🎁 专家福利系统设置完成！")
