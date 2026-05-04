#!/usr/bin/env python3
"""
整理任务列表并生成Excel文档
"""

import csv
from datetime import datetime
import os

# 任务数据
tasks = [
    # 已完成
    {"时间": "07:35", "任务": "读取2026-03-24的OpenClaw配置优化会话", "状态": "✅ 已完成", "分类": "配置", "备注": "找到完整会话记录"},
    {"时间": "07:42", "任务": "修复OpenClaw默认模型配置", "状态": "✅ 已完成", "分类": "配置", "备注": "改为ollama-cloud/glm-5:cloud"},
    {"时间": "07:47", "任务": "验证昨天股票持仓数据", "状态": "✅ 已完成", "分类": "股票", "备注": "士兰微600460, 华联股份000882"},
    {"时间": "07:52", "任务": "确认AI智能体执行流程", "状态": "✅ 已完成", "分类": "AI", "备注": "Think → Code → Execute → Learn → Repeat"},
    {"时间": "07:57", "任务": "创建想法记录系统", "状态": "✅ 已完成", "分类": "系统", "备注": "daily-ideas-2026-03-24.md"},
    {"时间": "07:58", "任务": "设置定期反馈机制", "状态": "✅ 已完成", "分类": "系统", "备注": "HEARTBEAT.md"},
    {"时间": "08:00", "任务": "创建发音规则文件", "状态": "✅ 已完成", "分类": "系统", "备注": "语音输入处理规范，闽南语发音特点"},
    {"时间": "08:04", "任务": "创建会话管理工具", "状态": "✅ 已完成", "分类": "系统", "备注": "session-manager.sh"},
    {"时间": "08:06", "任务": "设置09:15集合竞价分析", "状态": "✅ 已完成", "分类": "股票", "备注": "定时任务已创建"},
    {"时间": "08:09", "任务": "创建盘前数据分析脚本", "状态": "✅ 已完成", "分类": "股票", "备注": "pre_market_analysis.py"},
    
    # 进行中
    {"时间": "08:09", "任务": "整理任务列表为Excel", "状态": "🔄 进行中", "分类": "系统", "备注": "当前任务"},
    
    # 未完成
    {"时间": "08:04", "任务": "确认华联股份成本价", "状态": "⏳ 未完成", "分类": "股票", "备注": "两个版本：¥2.90 vs ¥1.779"},
    {"时间": "08:06", "任务": "获取集合竞价数据", "状态": "⏳ 未完成", "分类": "股票", "备注": "等待09:15执行"},
    {"时间": "08:09", "任务": "获取A50期指数据", "状态": "⏳ 未完成", "分类": "股票", "备注": "接口失败，需修复"},
    {"时间": "08:09", "任务": "北向资金数据", "状态": "⏳ 未完成", "分类": "股票", "备注": "未获取"},
    {"时间": "08:09", "任务": "龙虎榜数据", "状态": "⏳ 未完成", "分类": "股票", "备注": "未获取"},
]

def create_excel():
    """创建Excel文档（CSV格式）"""
    output_dir = "/root/.openclaw/workspace/reports"
    os.makedirs(output_dir, exist_ok=True)
    
    filename = f"{output_dir}/任务清单_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
    
    # 写入CSV（Excel可直接打开）
    with open(filename, 'w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        
        # 标题
        writer.writerow(["时间", "任务", "状态", "分类", "备注"])
        
        # 分类：已完成
        writer.writerow([])
        writer.writerow(["==== 已完成的任务 ====", "", "", "", ""])
        for task in tasks:
            if task["状态"] == "✅ 已完成":
                writer.writerow([task["时间"], task["任务"], task["状态"], task["分类"], task["备注"]])
        
        # 分类：进行中
        writer.writerow([])
        writer.writerow(["==== 进行中的任务 ====", "", "", "", ""])
        for task in tasks:
            if task["状态"] == "🔄 进行中":
                writer.writerow([task["时间"], task["任务"], task["状态"], task["分类"], task["备注"]])
        
        # 分类：未完成
        writer.writerow([])
        writer.writerow(["==== 未完成的任务 ====", "", "", "", ""])
        for task in tasks:
            if task["状态"] == "⏳ 未完成":
                writer.writerow([task["时间"], task["任务"], task["状态"], task["分类"], task["备注"]])
        
        # 统计
        completed = len([t for t in tasks if t["状态"] == "✅ 已完成"])
        in_progress = len([t for t in tasks if t["状态"] == "🔄 进行中"])
        pending = len([t for t in tasks if t["状态"] == "⏳ 未完成"])
        
        writer.writerow([])
        writer.writerow(["==== 统计 ====", "", "", "", ""])
        writer.writerow(["已完成", completed, "个", "", ""])
        writer.writerow(["进行中", in_progress, "个", "", ""])
        writer.writerow(["未完成", pending, "个", "", ""])
        writer.writerow(["总计", len(tasks), "个", "", ""])
    
    print(f"✅ Excel文档已生成")
    print(f"📁 文件位置: {filename}")
    
    # 同时生成一个更友好的Markdown版本
    md_filename = f"{output_dir}/任务清单_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
    
    with open(md_filename, 'w', encoding='utf-8') as f:
        f.write(f"# 任务清单 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n")
        
        f.write("## ✅ 已完成的任务\n\n")
        f.write("| 时间 | 任务 | 分类 | 备注 |\n")
        f.write("|------|------|------|------|\n")
        for task in tasks:
            if task["状态"] == "✅ 已完成":
                f.write(f"| {task['时间']} | {task['任务']} | {task['分类']} | {task['备注']} |\n")
        
        f.write("\n## 🔄 进行中的任务\n\n")
        f.write("| 时间 | 任务 | 分类 | 备注 |\n")
        f.write("|------|------|------|------|\n")
        for task in tasks:
            if task["状态"] == "🔄 进行中":
                f.write(f"| {task['时间']} | {task['任务']} | {task['分类']} | {task['备注']} |\n")
        
        f.write("\n## ⏳ 未完成的任务\n\n")
        f.write("| 时间 | 任务 | 分类 | 备注 |\n")
        f.write("|------|------|------|------|\n")
        for task in tasks:
            if task["状态"] == "⏳ 未完成":
                f.write(f"| {task['时间']} | {task['任务']} | {task['分类']} | {task['备注']} |\n")
        
        f.write("\n## 📊 统计\n\n")
        f.write(f"- 已完成: {completed} 个\n")
        f.write(f"- 进行中: {in_progress} 个\n")
        f.write(f"- 未完成: {pending} 个\n")
        f.write(f"- 总计: {len(tasks)} 个\n")
    
    print(f"✅ Markdown文档已生成")
    print(f"📁 文件位置: {md_filename}")
    
    return filename, md_filename

def main():
    print("="*60)
    print("📊 任务清单整理")
    print(f"时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    csv_file, md_file = create_excel()
    
    # 统计
    completed = len([t for t in tasks if t["状态"] == "✅ 已完成"])
    in_progress = len([t for t in tasks if t["状态"] == "🔄 进行中"])
    pending = len([t for t in tasks if t["状态"] == "⏳ 未完成"])
    
    print("\n" + "="*60)
    print("📊 任务统计")
    print("="*60)
    print(f"✅ 已完成: {completed} 个")
    print(f"🔄 进行中: {in_progress} 个")
    print(f"⏳ 未完成: {pending} 个")
    print(f"📝 总计: {len(tasks)} 个")

if __name__ == "__main__":
    main()