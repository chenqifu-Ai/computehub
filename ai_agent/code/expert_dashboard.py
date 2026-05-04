#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
专家表盘状态监控系统
用表盘方式展示7个专家的实时状态
"""

import os
import time
from datetime import datetime

def get_expert_status(expert_name):
    """获取单个专家的状态"""
    log_dir = "/root/.openclaw/workspace/expert_work_logs"
    
    # 查找该专家的最新报告
    expert_files = []
    if os.path.exists(log_dir):
        for file in os.listdir(log_dir):
            # 更宽松的匹配条件
            expert_search_name = expert_name.replace("💰", "").replace("📊", "").replace("⚖️", "").replace("💻", "").replace("🚀", "").replace("🎯", "").replace("👥", "").strip()
            if expert_search_name in file and "report" in file:
                expert_files.append(file)
    
    if len(expert_files) == 0:
        return "⚫ 离线", "无工作报告", "-"
    
    # 获取最新报告的时间
    latest_file = max(expert_files, key=lambda f: os.path.getmtime(os.path.join(log_dir, f)))
    report_time = os.path.getmtime(os.path.join(log_dir, latest_file))
    time_diff = time.time() - report_time
    
    # 根据时间差确定状态
    if time_diff < 3600:  # 1小时内
        status = "🟢 活跃"
        detail = "近期有工作"
    elif time_diff < 7200:  # 2小时内
        status = "🟡 待机"
        detail = "工作较旧"
    else:
        status = "🔴 休眠"
        detail = "长时间无工作"
    
    # 格式化时间
    last_work = datetime.fromtimestamp(report_time).strftime("%H:%M")
    
    return status, detail, last_work

def create_expert_dashboard():
    """创建专家表盘监控面板"""
    print("\n" + "="*70)
    print("👥  证券公司 - 专家表盘状态监控")
    print("="*70)
    
    # 7个专家的配置
    experts = [
        ("💰 金算子", "金融顾问", "股票分析交易"),
        ("📊 财神爷", "财务专家", "财务分析盈亏"),
        ("⚖️ 法海", "法律顾问", "风险评估合规"),
        ("💻 码神", "网络专家", "系统技术优化"),
        ("🚀 销冠王", "营销专家", "客户市场开发"),
        ("🎯 智多星", "CEO顾问", "战略规划并购"),
        ("👥 人精", "HR专家", "绩效考核管理")
    ]
    
    # 获取每个专家的状态
    expert_statuses = []
    for emoji_name, role, responsibility in experts:
        status, detail, last_work = get_expert_status(emoji_name.replace(" ", "").replace("💰", "金算子").replace("📊", "财神爷").replace("⚖️", "法海").replace("💻", "码神").replace("🚀", "销冠王").replace("🎯", "智多星").replace("👥", "人精"))
        expert_statuses.append({
            "name": emoji_name,
            "role": role,
            "responsibility": responsibility,
            "status": status,
            "detail": detail,
            "last_work": last_work
        })
    
    # 显示专家表盘
    for expert in expert_statuses:
        print(f"\n{expert['name']} - {expert['role']}")
        print(f"   📋 职责: {expert['responsibility']}")
        print(f"   🎯 状态: {expert['status']}")
        print(f"   📊 详情: {expert['detail']}")
        print(f"   ⏰ 最后工作: {expert['last_work']}")
    
    # 统计状态
    active_count = sum(1 for e in expert_statuses if "🟢" in e["status"])
    standby_count = sum(1 for e in expert_statuses if "🟡" in e["status"])
    sleep_count = sum(1 for e in expert_statuses if "🔴" in e["status"])
    offline_count = sum(1 for e in expert_statuses if "⚫" in e["status"])
    
    print("\n" + "="*70)
    print("📊 专家状态统计:")
    print(f"   🟢 活跃: {active_count}/7")
    print(f"   🟡 待机: {standby_count}/7") 
    print(f"   🔴 休眠: {sleep_count}/7")
    print(f"   ⚫ 离线: {offline_count}/7")
    
    # 总体状态
    if active_count >= 5:
        overall_status = "🟢 优秀"
    elif active_count >= 3:
        overall_status = "🟡 良好"
    else:
        overall_status = "🔴 需关注"
    
    print(f"\n🎯 专家团队总体状态: {overall_status}")
    print(f"⏰ 更新时间: {datetime.now().strftime('%H:%M:%S')}")
    print("="*70)
    
    # 表盘指示器说明
    print("\n🎛️ 表盘指示器说明:")
    print("🟢 活跃 - 1小时内有工作")
    print("🟡 待机 - 1-2小时内有工作") 
    print("🔴 休眠 - 2小时以上无工作")
    print("⚫ 离线 - 无工作报告")
    
    return expert_statuses

def save_expert_report(expert_data):
    """保存专家状态报告"""
    report_dir = "/root/.openclaw/workspace/ai_agent/results"
    os.makedirs(report_dir, exist_ok=True)
    
    import json
    report_file = os.path.join(report_dir, f"expert_dashboard_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json")
    
    with open(report_file, 'w', encoding='utf-8') as f:
        json.dump(expert_data, f, ensure_ascii=False, indent=2)
    
    return report_file

if __name__ == "__main__":
    # 创建专家表盘监控
    expert_data = create_expert_dashboard()
    
    # 保存报告
    report_file = save_expert_report(expert_data)
    print(f"\n📊 专家表盘报告已保存: {report_file}")
    
    print("\n🎯 专家表盘监控系统就绪！")