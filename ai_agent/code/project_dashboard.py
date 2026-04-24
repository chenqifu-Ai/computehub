#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
项目状态表盘展示
基于MEMORY.md中的项目信息生成可视化表盘
"""

import math
import time
from datetime import datetime

def create_dashboard():
    """创建项目状态表盘"""
    
    # 项目数据从MEMORY.md中提取
    projects = [
        {
            "name": "AI智能体框架开发",
            "priority": "P0",
            "status": "🟢 85%完成",
            "progress": 85,
            "category": "技术基石",
            "description": "公司技术基础"
        },
        {
            "name": "专家知识系统建设",
            "priority": "P0",
            "status": "🟢 84%完成",
            "progress": 84,
            "category": "技术基石",
            "description": "核心竞争力"
        },
        {
            "name": "Stream运营系统",
            "priority": "P1",
            "status": "🟢 100%完成",
            "progress": 100,
            "category": "运营基础",
            "description": "自主运行能力"
        },
        {
            "name": "监控预警系统优化",
            "priority": "P1",
            "status": "🟡 70%完成",
            "progress": 70,
            "category": "运营基础",
            "description": "风险控制保障"
        },
        {
            "name": "投资管理服务Demo",
            "priority": "P2",
            "status": "🟢 80%完成",
            "progress": 80,
            "category": "商业验证",
            "description": "技术验证案例"
        },
        {
            "name": "连续流技能研发",
            "priority": "P2",
            "status": "🟡 50%完成",
            "progress": 50,
            "category": "商业验证",
            "description": "技术创新探索"
        },
        {
            "name": "OpenRemoteAI项目",
            "priority": "P3",
            "status": "🔴 被遗漏",
            "progress": 0,
            "category": "商业转化",
            "description": "急需重启"
        },
        {
            "name": "企业AI咨询服务",
            "priority": "P3",
            "status": "🟡 10%规划",
            "progress": 10,
            "category": "商业转化",
            "description": "商业收入来源"
        }
    ]
    
    # 股票持仓信息
    stock_info = {
        "华联股份": {
            "code": "000882",
            "quantity": "13,500股",
            "cost_price": "¥1.873",
            "current_price": "¥1.66",
            "profit_loss": "-11.37% (-¥2,875.50)",
            "status": "⚠️ 接近止损"
        },
        "中远海发": {
            "code": "601866",
            "status": "👀 关注中",
            "current_price": "¥2.78",
            "buy_range": "¥2.50-2.70"
        }
    }
    
    # 系统状态
    system_status = {
        "OpenClaw": "🟢 运行中",
        "Ollama Cloud": "🟢 正常",
        "邮件系统": "🟢 正常",
        "监控系统": "🟡 优化中"
    }
    
    return projects, stock_info, system_status

def draw_gauge(progress, width=20):
    """绘制进度条表盘"""
    filled = int(width * progress / 100)
    empty = width - filled
    bar = "█" * filled + "░" * empty
    return f"[{bar}] {progress}%"

def draw_radial_gauge(progress, radius=8):
    """绘制圆形表盘"""
    # 简化的圆形表盘
    if progress == 100:
        return "🟢 ●●●●●●●●●●"
    elif progress >= 80:
        return "🟢 ●●●●●●●●○○"
    elif progress >= 60:
        return "🟡 ●●●●●●○○○○"
    elif progress >= 40:
        return "🟡 ●●●●○○○○○○"
    elif progress >= 20:
        return "🟠 ●●○○○○○○○○"
    else:
        return "🔴 ●○○○○○○○○○"

def generate_dashboard():
    """生成完整的表盘式项目状态展示"""
    
    projects, stock_info, system_status = create_dashboard()
    
    dashboard = ""
    dashboard += "=" * 60 + "\n"
    dashboard += "📊 项目状态表盘展示\n"
    dashboard += f"更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    dashboard += "=" * 60 + "\n\n"
    
    # 项目表盘区域
    dashboard += "🎯 项目状态表盘\n"
    dashboard += "-" * 40 + "\n"
    
    for project in projects:
        gauge = draw_radial_gauge(project['progress'])
        dashboard += f"{project['priority']} | {gauge} | {project['name']}\n"
        dashboard += f"     📍 {project['category']} | 📝 {project['description']}\n"
        dashboard += f"     📊 {draw_gauge(project['progress'])} | {project['status']}\n\n"
    
    # 股票表盘区域
    dashboard += "📈 股票持仓表盘\n"
    dashboard += "-" * 40 + "\n"
    
    for stock_name, info in stock_info.items():
        if stock_name == "华联股份":
            # 计算华联股份的进度（相对于止损位）
            current_price = float(info['current_price'].replace('¥', ''))
            stop_loss = 1.60
            target_price = 2.00
            
            # 计算风险进度（0% = 止损位，100% = 止盈位）
            risk_progress = max(0, min(100, (current_price - stop_loss) / (target_price - stop_loss) * 100))
            
            gauge = draw_radial_gauge(int(risk_progress))
            dashboard += f"{info['status']} | {gauge} | {stock_name}({info['code']})\n"
            dashboard += f"     📊 持仓: {info['quantity']} | 成本: {info['cost_price']}\n"
            dashboard += f"     💰 现价: {info['current_price']} | 盈亏: {info['profit_loss']}\n"
        else:
            dashboard += f"{info['status']} | 🟡 ●●○○○○○○○○ | {stock_name}({info['code']})\n"
            dashboard += f"     💰 现价: {info['current_price']} | 买入区间: {info['buy_range']}\n"
        dashboard += "\n"
    
    # 系统状态表盘
    dashboard += "⚙️ 系统状态表盘\n"
    dashboard += "-" * 40 + "\n"
    
    for system, status in system_status.items():
        if "🟢" in status:
            gauge = "🟢 ●●●●●●●●●●"
        elif "🟡" in status:
            gauge = "🟡 ●●●●●●○○○○"
        else:
            gauge = "🔴 ●○○○○○○○○○"
        
        dashboard += f"{gauge} | {system}: {status}\n"
    
    # 项目统计
    dashboard += "\n📊 项目组合统计\n"
    dashboard += "-" * 40 + "\n"
    
    total_projects = len(projects)
    completed = len([p for p in projects if p['progress'] >= 90])
    in_progress = len([p for p in projects if 20 <= p['progress'] < 90])
    not_started = len([p for p in projects if p['progress'] < 20])
    
    tech_projects = len([p for p in projects if "技术" in p['category']])
    business_projects = len([p for p in projects if "商业" in p['category']])
    
    dashboard += f"总项目数: {total_projects} | 技术类: {tech_projects} | 商业类: {business_projects}\n"
    dashboard += f"完成度: {completed}/{total_projects} | 进行中: {in_progress}/{total_projects} | 未开始: {not_started}/{total_projects}\n"
    
    # 整体进度
    avg_progress = sum(p['progress'] for p in projects) / len(projects)
    dashboard += f"整体进度: {draw_gauge(int(avg_progress))}\n"
    
    return dashboard

if __name__ == "__main__":
    try:
        dashboard = generate_dashboard()
        print(dashboard)
        
        # 保存到文件
        with open("/root/.openclaw/workspace/ai_agent/results/project_dashboard.txt", "w", encoding="utf-8") as f:
            f.write(dashboard)
        
        print("\n✅ 表盘已保存到: /root/.openclaw/workspace/ai_agent/results/project_dashboard.txt")
        
    except Exception as e:
        print(f"❌ 生成表盘时出错: {e}")