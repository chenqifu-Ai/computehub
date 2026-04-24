#!/usr/bin/env python3
"""
🔴 CEO主动监控系统
不等不靠，主动发现问题！
"""

import subprocess
import json
from pathlib import Path
from datetime import datetime

class CEOProactiveMonitor:
    def __init__(self):
        self.alerts = []
        
    def check_all(self):
        """全面检查"""
        print(f"\n🔴 CEO主动检查 - {datetime.now().strftime('%H:%M:%S')}")
        print("="*70)
        
        # 1. 检查专家产出
        self.check_expert_output()
        
        # 2. 检查股票风险
        self.check_stock_risk()
        
        # 3. 检查系统健康
        self.check_system_health()
        
        # 4. 检查制作产能
        self.check_production_capacity()
        
        # 5. 检查码神数据抓取
        self.check_data_capture()
        
        # 汇总
        print("\n" + "="*70)
        if self.alerts:
            print(f"🚨 发现 {len(self.alerts)} 个问题！")
            for alert in self.alerts:
                print(f"   {alert}")
        else:
            print("✅ 一切正常！")
        print("="*70)
        
    def check_expert_output(self):
        """检查专家产出"""
        experts = [
            ('码神', 'network-expert'),
            ('销冠王', 'marketing-expert'),
            ('金算子', 'finance-expert'),
            ('财神爷', 'finance-advisor'),
            ('人精', 'hr-expert'),
            ('法海', 'legal-advisor'),
            ('智多星', 'ceo-advisor')
        ]
        
        no_output = []
        for name, expert_id in experts:
            daily_file = Path(f'/root/.openclaw/workspace/skills/{expert_id}/daily/2026-03-29.md')
            if not daily_file.exists():
                no_output.append(name)
        
        if len(no_output) > 3:
            self.alerts.append(f"【专家产出】{len(no_output)}位专家未产出！")
            
    def check_stock_risk(self):
        """检查股票风险"""
        stock_file = Path('/root/.openclaw/workspace/ai_agent/results/stock_holdings.json')
        if stock_file.exists():
            with open(stock_file, 'r') as f:
                stocks = json.load(f)
            
            for stock in stocks:
                pnl = stock.get('浮动盈亏', '')
                if '-' in pnl:
                    self.alerts.append(f"【股票风险】{stock.get('股票', '')} {pnl}")
                    
    def check_system_health(self):
        """检查系统健康"""
        result = subprocess.run(['uptime'], capture_output=True, text=True)
        if 'load average' in result.stdout:
            load = float(result.stdout.split('load average:')[1].split(',')[0].strip())
            if load > 10:
                self.alerts.append(f"【系统负载】CPU负载过高: {load}")
                
    def check_production_capacity(self):
        """检查制作产能"""
        # 从脉搏日志中读取
        pulse_log = Path('/root/.openclaw/workspace/ai_agent/results/pulse_log.md')
        if pulse_log.exists():
            with open(pulse_log, 'r') as f:
                content = f.read()
            if '产出低于目标' in content[-5000:]:  # 检查最近内容
                self.alerts.append("【制作产能】产出低于目标！")
                
    def check_data_capture(self):
        """检查码神数据抓取"""
        data_file = Path('/root/.openclaw/workspace/skills/network-expert/data/captured_data.json')
        if not data_file.exists():
            self.alerts.append("【数据抓取】码神未抓取数据！")

if __name__ == "__main__":
    monitor = CEOProactiveMonitor()
    monitor.check_all()
