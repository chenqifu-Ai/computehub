#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
财务部数据检查脚本
执行：1. 计算当日成本支出 2. 跟踪收入数据 3. 计算ROI 4. 风险预警检查
"""

import json
import os
from datetime import datetime, timedelta

class FinanceChecker:
    def __init__(self):
        self.workspace_path = "/root/.openclaw/workspace"
        self.reports_path = os.path.join(self.workspace_path, "reports")
        self.daily_path = os.path.join(self.reports_path, "daily")
        self.finance_path = os.path.join(self.reports_path, "finance_info")
        
        # 财务数据模板
        self.finance_data = {
            "date": datetime.now().strftime("%Y-%m-%d"),
            "timestamp": datetime.now().isoformat(),
            "costs": {
                "daily_operating_cost": 15.0,  # 默认每日运营成本
                "investment_cost": 0.0,
                "total_cost": 15.0
            },
            "revenue": {
                "investment_income": 0.0,
                "other_income": 0.0,
                "total_revenue": 0.0
            },
            "investment": {
                "total_invested": 69569.0,
                "current_value": 65208.0,
                "profit_loss": -4361.0,
                "roi": -0.0627
            },
            "risk_alerts": []
        }
    
    def load_daily_reports(self):
        """加载每日报告数据"""
        daily_files = []
        try:
            for file in os.listdir(self.daily_path):
                if file.startswith("daily_report_") and file.endswith(".md"):
                    daily_files.append(os.path.join(self.daily_path, file))
        except Exception as e:
            print(f"加载每日报告错误: {e}")
            return []
        
        return sorted(daily_files, reverse=True)
    
    def parse_daily_report(self, file_path):
        """解析每日报告"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 提取投资数据
            lines = content.split('\n')
            investment_data = {}
            
            for line in lines:
                if '总投入：' in line:
                    investment_data['total_invested'] = float(line.split('：')[1].replace('¥', '').replace(',', ''))
                elif '当前市值：' in line:
                    investment_data['current_value'] = float(line.split('：')[1].replace('¥', '').replace(',', ''))
                elif '总盈亏：' in line:
                    parts = line.split('：')[1].split('(')
                    investment_data['profit_loss'] = float(parts[0].replace('¥', '').replace(',', ''))
                    if len(parts) > 1:
                        investment_data['roi'] = float(parts[1].replace('%)', '').replace('%', '')) / 100
            
            return investment_data
        except Exception as e:
            print(f"解析报告错误 {file_path}: {e}")
            return {}
    
    def calculate_daily_costs(self):
        """计算当日成本支出"""
        # 这里可以添加更复杂的成本计算逻辑
        # 目前使用默认值，后续可以集成实际的成本数据
        return {
            "daily_operating_cost": 15.0,  # 每日运营成本
            "investment_cost": 0.0,       # 投资相关成本
            "total_cost": 15.0            # 总成本
        }
    
    def track_revenue_data(self):
        """跟踪收入数据"""
        # 从投资数据中提取收入信息
        daily_files = self.load_daily_reports()
        if not daily_files:
            return {"total_revenue": 0.0}
        
        # 获取最新报告
        latest_report = self.parse_daily_report(daily_files[0])
        
        return {
            "investment_income": latest_report.get('profit_loss', 0.0),
            "total_revenue": latest_report.get('profit_loss', 0.0)
        }
    
    def calculate_roi(self):
        """计算ROI"""
        daily_files = self.load_daily_reports()
        if not daily_files:
            return {"roi": 0.0}
        
        latest_report = self.parse_daily_report(daily_files[0])
        
        return {
            "total_invested": latest_report.get('total_invested', 0.0),
            "current_value": latest_report.get('current_value', 0.0),
            "profit_loss": latest_report.get('profit_loss', 0.0),
            "roi": latest_report.get('roi', 0.0)
        }
    
    def check_risk_alerts(self):
        """风险预警检查"""
        alerts = []
        
        # 获取投资数据
        investment_data = self.calculate_roi()
        
        # 检查亏损风险
        if investment_data.get('profit_loss', 0) < -5000:
            alerts.append({
                "type": "投资亏损",
                "level": "高风险",
                "message": f"投资亏损已达 ¥{investment_data['profit_loss']:.2f}，超过预警阈值",
                "suggestion": "考虑止损或调整投资策略"
            })
        
        # 检查成本超支
        costs = self.calculate_daily_costs()
        if costs['total_cost'] > 15.0:
            alerts.append({
                "type": "成本超支", 
                "level": "中风险",
                "message": f"当日成本 ¥{costs['total_cost']:.2f} 超过预算",
                "suggestion": "审查成本结构，优化支出"
            })
        
        # 检查ROI过低
        if investment_data.get('roi', 0) < -0.05:
            alerts.append({
                "type": "ROI过低",
                "level": "中风险", 
                "message": f"投资回报率 {investment_data['roi']*100:.2f}% 低于预期",
                "suggestion": "重新评估投资组合"
            })
        
        return alerts
    
    def generate_finance_report(self):
        """生成财务检查报告"""
        print("🔍 开始财务部数据检查...")
        
        # 执行各项检查
        costs = self.calculate_daily_costs()
        revenue = self.track_revenue_data()
        investment = self.calculate_roi()
        alerts = self.check_risk_alerts()
        
        # 更新财务数据
        self.finance_data['costs'] = costs
        self.finance_data['revenue'] = revenue
        self.finance_data['investment'] = investment
        self.finance_data['risk_alerts'] = alerts
        
        # 生成报告
        report = f"""# 📊 财务部数据检查报告

**检查时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## 1. 当日成本支出
- **运营成本**: ¥{costs['daily_operating_cost']:.2f}
- **投资成本**: ¥{costs['investment_cost']:.2f}
- **总成本**: ¥{costs['total_cost']:.2f}

## 2. 收入数据跟踪  
- **投资收入**: ¥{revenue['investment_income']:.2f}
- **总收入**: ¥{revenue['total_revenue']:.2f}

## 3. ROI计算
- **总投资**: ¥{investment['total_invested']:.2f}
- **当前市值**: ¥{investment['current_value']:.2f}
- **盈亏**: ¥{investment['profit_loss']:.2f}
- **ROI**: {investment['roi']*100:.2f}%

## 4. 风险预警检查
"""
        
        if alerts:
            report += "\n🚨 **风险预警发现**:\n"
            for alert in alerts:
                report += f"- **{alert['type']}** ({alert['level']}): {alert['message']}\n"
                report += f"  建议: {alert['suggestion']}\n"
        else:
            report += "\n✅ **无风险预警**\n"
        
        report += f"\n---\n**检查完成**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        return report
    
    def save_report(self, report):
        """保存报告"""
        # 确保目录存在
        os.makedirs(self.finance_path, exist_ok=True)
        
        # 生成文件名
        filename = f"finance_check_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
        filepath = os.path.join(self.finance_path, filename)
        
        # 保存文件
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(report)
        
        print(f"✅ 财务报告已保存: {filepath}")
        return filepath
    
    def update_finance_dashboard(self):
        """更新财务看板数据"""
        # 这里可以添加更新看板的逻辑
        # 目前先保存JSON格式的数据用于后续集成
        data_file = os.path.join(self.finance_path, "finance_data.json")
        
        with open(data_file, 'w', encoding='utf-8') as f:
            json.dump(self.finance_data, f, ensure_ascii=False, indent=2)
        
        print(f"✅ 财务数据已更新: {data_file}")

def main():
    """主函数"""
    checker = FinanceChecker()
    
    # 生成财务报告
    report = checker.generate_finance_report()
    print(report)
    
    # 保存报告
    report_path = checker.save_report(report)
    
    # 更新财务数据
    checker.update_finance_dashboard()
    
    return report_path

if __name__ == "__main__":
    main()