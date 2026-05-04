#!/usr/bin/env python3
"""
💓 小智影业 - 公司脉搏监控系统
每10分钟执行一次，检查各部门KPI
"""

from pathlib import Path
from datetime import datetime
import json

class CompanyPulse:
    def __init__(self):
        self.data_file = Path("/root/.openclaw/workspace/ai_agent/results/pulse_data.json")
        self.log_file = Path("/root/.openclaw/workspace/ai_agent/results/pulse_log.md")
        self.load_data()
        
    def load_data(self):
        """加载数据"""
        if self.data_file.exists():
            with open(self.data_file, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = self.init_data()
    
    def init_data(self):
        """初始化数据"""
        return {
            "company": "小智影业",
            "last_check": None,
            "departments": {
                "营销部": {"status": "待启动", "kpi": {}, "alerts": []},
                "制作部": {"status": "待启动", "kpi": {}, "alerts": []},
                "财务部": {"status": "待启动", "kpi": {}, "alerts": []},
                "数据部": {"status": "待启动", "kpi": {}, "alerts": []},
                "风控部": {"status": "待启动", "kpi": {}, "alerts": []}
            }
        }
    
    def check_pulse(self):
        """执行脉搏检查"""
        now = datetime.now()
        report = f"""
## 💓 公司脉搏检查报告

**检查时间**: {now.strftime('%Y-%m-%d %H:%M:%S')}
**公司**: 小智影业
**CEO**: 小智

---

### 📊 各部门状态

"""
        
        # 营销部检查
        营销_kpi = self.check_marketing()
        report += f"""
**【营销部】** (营销专家负责)
- 状态: {营销_kpi['status']}
- 今日发布: {营销_kpi.get('posts_today', 0)} 条
- 播放量: {营销_kpi.get('views_today', 0)} 次
- 粉丝增长: +{营销_kpi.get('fans_growth', 0)} 人
- ⚠️ 预警: {营销_kpi.get('alert', '无')}
"""
        
        # 制作部检查
        制作_kpi = self.check_production()
        report += f"""
**【制作部】** (HR专家负责)
- 状态: {制作_kpi['status']}
- 今日产出: {制作_kpi.get('output_today', 0)} 条
- 平均制作时间: {制作_kpi.get('avg_time', 0)} 小时/条
- 质检通过率: {制作_kpi.get('pass_rate', 0)}%
- ⚠️ 预警: {制作_kpi.get('alert', '无')}
"""
        
        # 财务部检查
        财务_kpi = self.check_finance()
        report += f"""
**【财务部】** (财务专家负责)
- 状态: {财务_kpi['status']}
- 今日成本: ¥{财务_kpi.get('cost_today', 0)}
- 今日收入: ¥{财务_kpi.get('revenue_today', 0)}
- 累计ROI: {财务_kpi.get('roi', 0)}%
- ⚠️ 预警: {财务_kpi.get('alert', '无')}
"""
        
        # 数据部检查
        数据_kpi = self.check_data()
        report += f"""
**【数据部】** (网络专家负责)
- 状态: {数据_kpi['status']}
- 竞品监控: {数据_kpi.get('competitors_tracked', 0)} 个
- 热点响应: {数据_kpi.get('hotspot_response', '正常')}
- 数据准确率: {数据_kpi.get('accuracy', 0)}%
- ⚠️ 预警: {数据_kpi.get('alert', '无')}
"""
        
        # 风控部检查
        风控_kpi = self.check_risk()
        report += f"""
**【风控部】** (法务专家负责)
- 状态: {风控_kpi['status']}
- 今日审核: {风控_kpi.get('contents_reviewed', 0)} 条
- 合规率: {风控_kpi.get('compliance_rate', 100)}%
- 风险事件: {风控_kpi.get('risk_events', 0)} 起
- ⚠️ 预警: {风控_kpi.get('alert', '无')}
"""
        
        report += f"""
---

### 📈 关键指标总览

| 指标 | 目标 | 当前 | 状态 |
|------|------|------|------|
| 日产量 | ≥3条 | {制作_kpi.get('output_today', 0)}条 | {'✅' if 制作_kpi.get('output_today', 0) >= 3 else '⚠️'} |
| 日播放量 | - | {营销_kpi.get('views_today', 0)}次 | 📊 |
| 日成本 | ≤¥10 | ¥{财务_kpi.get('cost_today', 0)} | {'✅' if 财务_kpi.get('cost_today', 0) <= 10 else '⚠️'} |
| 合规率 | 100% | {风控_kpi.get('compliance_rate', 100)}% | {'✅' if 风控_kpi.get('compliance_rate', 100) == 100 else '❌'} |

---

### 🚨 需CEO关注的事项

"""
        
        # 汇总所有预警
        alerts = []
        if 营销_kpi.get('alert'): alerts.append(f"【营销部】{营销_kpi['alert']}")
        if 制作_kpi.get('alert'): alerts.append(f"【制作部】{制作_kpi['alert']}")
        if 财务_kpi.get('alert'): alerts.append(f"【财务部】{财务_kpi['alert']}")
        if 数据_kpi.get('alert'): alerts.append(f"【数据部】{数据_kpi['alert']}")
        if 风控_kpi.get('alert'): alerts.append(f"【风控部】{风控_kpi['alert']}")
        
        if alerts:
            for alert in alerts:
                report += f"- {alert}\n"
        else:
            report += "- 暂无预警，公司运转正常 ✅\n"
        
        report += f"""

---

**下次检查**: {(now.replace(second=0, microsecond=0) + __import__('datetime').timedelta(minutes=10)).strftime('%H:%M')}

---
"""
        
        return report
    
    # 模拟各部门检查（实际应该连接真实数据）
    def check_marketing(self):
        return {"status": "正常运营", "posts_today": 2, "views_today": 8500, "fans_growth": 45, "alert": ""}
    
    def check_production(self):
        return {"status": "正常运营", "output_today": 2, "avg_time": 2.1, "pass_rate": 95, "alert": "产出低于目标"}
    
    def check_finance(self):
        return {"status": "正常运营", "cost_today": 7, "revenue_today": 0, "roi": -100, "alert": ""}
    
    def check_data(self):
        return {"status": "正常运营", "competitors_tracked": 5, "hotspot_response": "正常", "accuracy": 98, "alert": ""}
    
    def check_risk(self):
        return {"status": "正常运营", "contents_reviewed": 2, "compliance_rate": 100, "risk_events": 0, "alert": ""}
    
    def save_log(self, report):
        """保存日志"""
        with open(self.log_file, 'a', encoding='utf-8') as f:
            f.write(report)
            f.write("\n\n")
    
    def run(self):
        """执行脉搏检查"""
        report = self.check_pulse()
        self.save_log(report)
        print(report)
        return report

if __name__ == "__main__":
    pulse = CompanyPulse()
    pulse.run()
