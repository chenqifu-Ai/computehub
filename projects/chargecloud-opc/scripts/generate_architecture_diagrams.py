#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChargeCloud OPC 架构图生成器
生成 PNG/SVG 格式的架构图并准备邮件发送

创建时间：2026-04-19
作者：小智 (数据智能体)
"""

import os
import sys
from datetime import datetime

# 检查依赖
try:
    import graphviz
    GRAPHVIZ_AVAILABLE = True
except ImportError:
    GRAPHVIZ_AVAILABLE = False
    print("⚠️  graphviz 未安装，将使用 ASCII 艺术图生成")

try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    print("⚠️  Pillow 未安装，将无法生成 PNG")

# 输出目录
OUTPUT_DIR = "/root/.openclaw/workspace/projects/chargecloud-opc/architecture-images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

print("=" * 60)
print("ChargeCloud OPC 架构图生成器")
print("=" * 60)
print(f"输出目录：{OUTPUT_DIR}")
print(f"生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# 图 1: 整体架构图 (Graphviz DOT)
def generate_overall_architecture():
    """生成整体架构图"""
    if not GRAPHVIZ_AVAILABLE:
        print("⚠️  跳过整体架构图 (需要 graphviz)")
        return None
    
    dot = graphviz.Digraph('overall_architecture', comment='ChargeCloud Overall Architecture')
    dot.attr(rankdir='TB')
    dot.attr('node', shape='box', style='filled', fontname='Microsoft YaHei')
    
    # 人类 CEO
    dot.node('human_ceo', '👤 人类 CEO / 管理层\n(战略审批/重大决策)', fillcolor='#FFE4B5')
    
    # CEO 智能体
    dot.node('ceo_agent', '🤵 CEO 智能体\nqwen3.5:397b | 262k 上下文\n战略规划 | 资源分配 | 决策', fillcolor='#FFD700')
    
    # 部门智能体
    dot.node('marketing', '📈 营销智能体\nqwen3.5:35b\n市场推广 | 用户增长', fillcolor='#98FB98')
    dot.node('operations', '⚙️ 运营智能体\nqwen3.5:35b\n设备管理 | 订单处理', fillcolor='#87CEEB')
    dot.node('finance', '💰 财务智能体\nqwen3.5:35b\n财务核算 | 成本控制', fillcolor='#DDA0DD')
    
    # 数据智能体
    dot.node('data_agent', '📊 数据智能体\nqwen3.5:35b\n数据采集 | 分析 | 预测', fillcolor='#F0E68C')
    
    # 数据层
    dot.node('mysql', '🗄️ MySQL\n业务数据库', fillcolor='#D3D3D3')
    dot.node('redis', '🔴 Redis\n缓存层', fillcolor='#FFB6C1')
    dot.node('minio', '📦 MinIO\n文件存储', fillcolor='#D3D3D3')
    
    # 连接关系
    dot.edge('human_ceo', 'ceo_agent', '汇报/审批')
    dot.edge('ceo_agent', 'marketing', '指令')
    dot.edge('ceo_agent', 'operations', '指令')
    dot.edge('ceo_agent', 'finance', '指令')
    dot.edge('marketing', 'data_agent', '数据请求')
    dot.edge('operations', 'data_agent', '数据请求')
    dot.edge('finance', 'data_agent', '数据请求')
    dot.edge('data_agent', 'mysql', '')
    dot.edge('data_agent', 'redis', '')
    dot.edge('data_agent', 'minio', '')
    
    # 保存
    output_path = os.path.join(OUTPUT_DIR, '01_overall_architecture')
    dot.render(output_path, format='png', cleanup=True)
    dot.render(output_path, format='svg', cleanup=True)
    
    print(f"✅ 整体架构图已生成:")
    print(f"   PNG:  {output_path}.png")
    print(f"   SVG:  {output_path}.svg")
    
    return output_path

# 图 2: 日常运营流程图
def generate_daily_operations_flow():
    """生成日常运营流程图"""
    if not GRAPHVIZ_AVAILABLE:
        print("⚠️  跳过日常运营流程图 (需要 graphviz)")
        return None
    
    dot = graphviz.Digraph('daily_flow', comment='Daily Operations Flow')
    dot.attr(rankdir='TB')
    dot.attr('node', shape='box', style='filled,frounded', fontname='Microsoft YaHei')
    
    # 时间节点
    times = [
        ('06:00', '📊 数据采集\n数据智能体采集夜间数据', '#E0F7FA'),
        ('07:00', '📝 部门日报\n各智能体生成部门报告', '#FFF3E0'),
        ('08:00', '📊 数据汇总\n数据智能体汇总分析', '#E8F5E9'),
        ('09:00', '🤵 CEO 审阅\n审阅日报并发出指令', '#FFD700'),
        ('09:30', '⚡ 任务执行\n各智能体执行当日任务', '#E3F2FD'),
        ('12:00', '⚖️ 合规检查\n风控智能体午间检查', '#F3E5F5'),
        ('18:00', '📝 部门晚报\n各智能体生成晚报', '#FFF9C4'),
        ('20:00', '🤵 经营日报\nCEO 生成并发送报告', '#FFCCBC'),
        ('22:00', '💾 数据备份\n数据智能体备份归档', '#CFD8DC'),
    ]
    
    prev_node = None
    for time, label, color in times:
        node_id = f'time_{time.replace(":", "_")}'
        dot.node(node_id, f'{time}\n{label}', fillcolor=color)
        if prev_node:
            dot.edge(prev_node, node_id, '')
        prev_node = node_id
    
    # 保存
    output_path = os.path.join(OUTPUT_DIR, '02_daily_operations_flow')
    dot.render(output_path, format='png', cleanup=True)
    dot.render(output_path, format='svg', cleanup=True)
    
    print(f"✅ 日常运营流程图已生成:")
    print(f"   PNG:  {output_path}.png")
    print(f"   SVG:  {output_path}.svg")
    
    return output_path

# 图 3: 重大决策流程图
def generate_decision_flow():
    """生成重大决策流程图"""
    if not GRAPHVIZ_AVAILABLE:
        print("⚠️  跳过重大决策流程图 (需要 graphviz)")
        return None
    
    dot = graphviz.Digraph('decision_flow', comment='Major Decision Flow')
    dot.attr(rankdir='TB')
    dot.attr('node', shape='box', style='filled,frounded', fontname='Microsoft YaHei')
    
    # 决策步骤
    steps = [
        ('step1', '1️⃣ 问题识别\n📊 数据智能体发现异常', '#E0F7FA'),
        ('step2', '2️⃣ 分析评估\n相关部门智能体深度分析', '#FFF3E0'),
        ('step3', '3️⃣ 方案制定\n多智能体协作制定方案', '#E8F5E9'),
        ('step4', '4️⃣ 风险评估\n⚖️ 风控智能体评估风险', '#F3E5F5'),
        ('step5', '5️⃣ 财务测算\n💰 财务智能体 ROI 分析', '#FFF9C4'),
        ('step6', '6️⃣ CEO 决策\n🤵 CEO 智能体综合决策', '#FFD700'),
        ('step7', '7️⃣ 执行监控\n⚙️ 运营智能体执行', '#E3F2FD'),
        ('step8', '8️⃣ 效果评估\n📊 数据智能体评估效果', '#CFD8DC'),
    ]
    
    prev_node = None
    for node_id, label, color in steps:
        dot.node(node_id, label, fillcolor=color)
        if prev_node:
            dot.edge(prev_node, node_id, '')
        prev_node = node_id
    
    # 保存
    output_path = os.path.join(OUTPUT_DIR, '03_decision_flow')
    dot.render(output_path, format='png', cleanup=True)
    dot.render(output_path, format='svg', cleanup=True)
    
    print(f"✅ 重大决策流程图已生成:")
    print(f"   PNG:  {output_path}.png")
    print(f"   SVG:  {output_path}.svg")
    
    return output_path

# 图 4: 智能体组织架构图
def generate_org_chart():
    """生成智能体组织架构图"""
    if not GRAPHVIZ_AVAILABLE:
        print("⚠️  跳过组织架构图 (需要 graphviz)")
        return None
    
    dot = graphviz.Digraph('org_chart', comment='Agent Organization Chart')
    dot.attr(rankdir='TB')
    dot.attr('node', shape='box', style='filled,frounded', fontname='Microsoft YaHei')
    
    # 层级
    dot.node('human', '👤 人类 CEO\n最终决策权', fillcolor='#FFE4B5', shape='ellipse')
    
    with dot.subgraph(name='cluster_ceo') as c:
        c.attr(label='决策层', color='#FFD700', style='filled', fillcolor='#FFF8E1')
        c.node('ceo', '🤵 CEO 智能体\nqwen3.5:397b\n战略决策中枢', fillcolor='#FFD700')
    
    with dot.subgraph(name='cluster_dept') as c:
        c.attr(label='执行层', color='#90CAF9', style='filled', fillcolor='#E3F2FD')
        c.node('marketing', '📈 营销智能体\n市场增长', fillcolor='#98FB98')
        c.node('operations', '⚙️ 运营智能体\n业务执行', fillcolor='#87CEEB')
        c.node('finance', '💰 财务智能体\n资金管控', fillcolor='#DDA0DD')
        c.node('risk', '⚖️ 风控智能体\n安全合规', fillcolor='#FFB6C1')
    
    with dot.subgraph(name='cluster_support') as c:
        c.attr(label='支撑层', color='#A5D6A7', style='filled', fillcolor='#E8F5E9')
        c.node('data', '📊 数据智能体\n数据分析引擎', fillcolor='#F0E68C')
    
    # 连接
    dot.edge('human', 'ceo', '汇报/审批')
    dot.edge('ceo', 'marketing', '')
    dot.edge('ceo', 'operations', '')
    dot.edge('ceo', 'finance', '')
    dot.edge('ceo', 'risk', '')
    dot.edge('data', 'ceo', '数据支撑')
    
    # 保存
    output_path = os.path.join(OUTPUT_DIR, '04_org_chart')
    dot.render(output_path, format='png', cleanup=True)
    dot.render(output_path, format='svg', cleanup=True)
    
    print(f"✅ 智能体组织架构图已生成:")
    print(f"   PNG:  {output_path}.png")
    print(f"   SVG:  {output_path}.svg")
    
    return output_path

# 生成 ASCII 艺术图 (备用方案)
def generate_ascii_diagrams():
    """生成 ASCII 艺术图作为备用"""
    print("\n📝 生成 ASCII 艺术图 (备用方案)...")
    
    ascii_content = """
╔═══════════════════════════════════════════════════════════════════════════╗
║           ChargeCloud OPC - AI 智能体整体架构图                              ║
╠═══════════════════════════════════════════════════════════════════════════╣
║                                                                           ║
║                        👤 人类 CEO / 管理层                                 ║
║                     (战略审批 / 重大决策)                                  ║
║                                  │                                        ║
║                          汇报/审批 │                                      ║
║                                  ▼                                        ║
║  ╔═══════════════════════════════════════════════════════════════════╗   ║
║  ║  🤵 CEO 智能体 (决策层)                                              ║   ║
║  ║     模型：qwen3.5:397b | 262k 上下文                                 ║   ║
║  ║     战略规划 | 资源分配 | 目标管理 | 跨部门协调 | 重大决策            ║   ║
║  ╚═══════════════════════════════════════════════════════════════════╝   ║
║                                  │                                        ║
║              ┌───────────────────┼───────────────────┐                   ║
║              │                   │                   │                    ║
║              ▼                   ▼                   ▼                    ║
║  ╔═══════════════╗   ╔═══════════════╗   ╔═══════════════╗               ║
║  ║ 📈 营销智能体  ║   ║ ⚙️ 运营智能体  ║   ║ 💰 财务智能体  ║               ║
║  ║  市场增长引擎  ║   ║  业务执行核心  ║   ║  资金管控专家  ║               ║
║  ║  qwen3.5:35b  ║   ║  qwen3.5:35b  ║   ║  qwen3.5:35b  ║               ║
║  ║  6 个 KPI      ║   ║  6 个 KPI      ║   ║  7 个 KPI      ║               ║
║  ╚═══════════════╝   ╚═══════════════╝   ╚═══════════════╝               ║
║              │                   │                   │                    ║
║              └───────────────────┼───────────────────┘                   ║
║                                  │                                        ║
║                                  ▼                                        ║
║  ╔═══════════════════════════════════════════════════════════════════╗   ║
║  ║  📊 数据智能体 (支撑层)                                              ║   ║
║  ║     模型：qwen3.5:35b | 数据分析引擎                                 ║   ║
║  ║     数据采集 | 数据清洗 | 分析洞察 | 预测模型 | 可视化报告            ║   ║
║  ╚═══════════════════════════════════════════════════════════════════╝   ║
║                                  │                                        ║
║              ┌───────────────────┼───────────────────┐                   ║
║              │                   │                   │                    ║
║              ▼                   ▼                   ▼                    ║
║      ╔═══════════╗       ╔═══════════╗       ╔═══════════╗               ║
║      ║   MySQL   ║       ║   Redis   ║       ║   MinIO   ║               ║
║      ║  业务数据库 ║       ║   缓存层   ║       ║  文件存储  ║               ║
║      ╚═══════════╝       ╚═══════════╝       ╚═══════════╝               ║
║                                                                           ║
╚═══════════════════════════════════════════════════════════════════════════╝
"""
    
    ascii_path = os.path.join(OUTPUT_DIR, '00_overall_architecture_ascii.txt')
    with open(ascii_path, 'w', encoding='utf-8') as f:
        f.write(ascii_content)
    
    print(f"✅ ASCII 艺术图已生成：{ascii_path}")
    return ascii_path

# 主函数
def main():
    print("开始生成架构图...\n")
    
    # 尝试生成 Graphviz 图
    generate_overall_architecture()
    generate_daily_operations_flow()
    generate_decision_flow()
    generate_org_chart()
    
    # 生成 ASCII 备用图
    generate_ascii_diagrams()
    
    print("\n" + "=" * 60)
    print("架构图生成完成!")
    print("=" * 60)
    print(f"\n输出目录：{OUTPUT_DIR}")
    print("\n生成的文件:")
    for root, dirs, files in os.walk(OUTPUT_DIR):
        for file in sorted(files):
            filepath = os.path.join(root, file)
            size = os.path.getsize(filepath)
            print(f"  📄 {file} ({size:,} bytes)")
    
    print("\n✅ 准备发送邮件...")
    return OUTPUT_DIR

if __name__ == '__main__':
    output_dir = main()
    print(f"\n📧 下一步：将 {output_dir} 中的图片发送到 19525456@qq.com")
