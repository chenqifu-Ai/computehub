#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ChargeCloud OPC 架构图 HTML 邮件生成器
生成 HTML 格式的架构图邮件

创建时间：2026-04-19
作者：小智 (数据智能体)
"""

import os
from datetime import datetime

# 输出目录
OUTPUT_DIR = "/root/.openclaw/workspace/projects/chargecloud-opc/architecture-images"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# 生成 HTML 邮件内容
html_content = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>ChargeCloud OPC - AI 智能体架构图</title>
    <style>
        body {{
            font-family: 'Microsoft YaHei', 'Segoe UI', Arial, sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 1200px;
            margin: 0 auto;
            padding: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        }}
        .container {{
            background: white;
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
        }}
        h1 {{
            color: #667eea;
            text-align: center;
            font-size: 28px;
            margin-bottom: 10px;
        }}
        .subtitle {{
            text-align: center;
            color: #666;
            font-size: 14px;
            margin-bottom: 30px;
        }}
        .section {{
            margin: 30px 0;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
            border-left: 4px solid #667eea;
        }}
        .section h2 {{
            color: #667eea;
            font-size: 20px;
            margin-top: 0;
        }}
        .agent-box {{
            display: inline-block;
            padding: 15px 20px;
            margin: 10px;
            border-radius: 8px;
            text-align: center;
            font-weight: bold;
            box-shadow: 0 4px 15px rgba(0,0,0,0.1);
            min-width: 150px;
        }}
        .ceo {{ background: linear-gradient(135deg, #FFD700, #FFA500); color: #000; }}
        .marketing {{ background: linear-gradient(135deg, #98FB98, #32CD32); color: #000; }}
        .operations {{ background: linear-gradient(135deg, #87CEEB, #4169E1); color: #fff; }}
        .finance {{ background: linear-gradient(135deg, #DDA0DD, #9370DB); color: #fff; }}
        .data {{ background: linear-gradient(135deg, #F0E68C, #DAA520); color: #000; }}
        .risk {{ background: linear-gradient(135deg, #FFB6C1, #DC143C); color: #fff; }}
        .human {{ background: linear-gradient(135deg, #FFE4B5, #FFA500); color: #000; }}
        .database {{ background: linear-gradient(135deg, #D3D3D3, #808080); color: #000; }}
        .flow-container {{
            display: flex;
            flex-direction: column;
            align-items: center;
            margin: 20px 0;
        }}
        .flow-arrow {{
            font-size: 24px;
            color: #667eea;
            margin: 5px 0;
        }}
        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        .kpi-card {{
            background: white;
            padding: 15px;
            border-radius: 8px;
            border: 2px solid #e0e0e0;
        }}
        .kpi-card h3 {{
            margin: 0 0 10px 0;
            color: #667eea;
            font-size: 16px;
        }}
        .kpi-item {{
            display: flex;
            justify-content: space-between;
            padding: 5px 0;
            border-bottom: 1px solid #eee;
        }}
        .kpi-item:last-child {{
            border-bottom: none;
        }}
        .kpi-value {{
            font-weight: bold;
            color: #32CD32;
        }}
        .kpi-value.warning {{
            color: #FFA500;
        }}
        .kpi-value.danger {{
            color: #DC143C;
        }}
        .timeline {{
            position: relative;
            padding-left: 30px;
            margin: 20px 0;
        }}
        .timeline-item {{
            position: relative;
            padding-bottom: 20px;
            border-left: 2px solid #667eea;
            padding-left: 20px;
        }}
        .timeline-item::before {{
            content: '●';
            position: absolute;
            left: -8px;
            top: 0;
            color: #667eea;
            font-size: 16px;
        }}
        .timeline-time {{
            font-weight: bold;
            color: #667eea;
        }}
        pre {{
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 15px;
            border-radius: 8px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 12px;
        }}
        .footer {{
            text-align: center;
            margin-top: 30px;
            padding-top: 20px;
            border-top: 2px solid #e0e0e0;
            color: #666;
            font-size: 12px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th, td {{
            padding: 10px;
            text-align: left;
            border-bottom: 1px solid #ddd;
        }}
        th {{
            background: #667eea;
            color: white;
        }}
        tr:hover {{
            background: #f5f5f5;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🤖 ChargeCloud OPC - AI 智能体架构图</h1>
        <p class="subtitle">生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 版本：v1.0</p>
        
        <!-- 整体架构 -->
        <div class="section">
            <h2>📊 整体架构图</h2>
            <div class="flow-container">
                <div class="agent-box human">👤 人类 CEO<br><small>战略审批/重大决策</small></div>
                <div class="flow-arrow">↓ 汇报/审批</div>
                <div class="agent-box ceo" style="width: 400px;">
                    🤵 CEO 智能体<br>
                    <small>qwen3.5:397b | 262k 上下文</small><br>
                    <small>战略规划 | 资源分配 | 决策</small>
                </div>
                <div class="flow-arrow">↓ 指令下达</div>
                <div style="display: flex; flex-wrap: wrap; justify-content: center;">
                    <div class="agent-box marketing">📈 营销<br><small>市场增长</small></div>
                    <div class="agent-box operations">⚙️ 运营<br><small>业务执行</small></div>
                    <div class="agent-box finance">💰 财务<br><small>资金管控</small></div>
                    <div class="agent-box risk">⚖️ 风控<br><small>安全合规</small></div>
                </div>
                <div class="flow-arrow">↓ 数据请求</div>
                <div class="agent-box data" style="width: 300px;">
                    📊 数据智能体<br>
                    <small>qwen3.5:35b | 数据分析引擎</small>
                </div>
                <div class="flow-arrow">↓ 数据存储</div>
                <div style="display: flex; flex-wrap: wrap; justify-content: center;">
                    <div class="agent-box database">🗄️ MySQL<br><small>业务数据</small></div>
                    <div class="agent-box database">🔴 Redis<br><small>缓存</small></div>
                    <div class="agent-box database">📦 MinIO<br><small>文件</small></div>
                </div>
            </div>
        </div>
        
        <!-- 智能体配置总览 -->
        <div class="section">
            <h2>⚙️ 智能体配置总览</h2>
            <table>
                <tr>
                    <th>智能体</th>
                    <th>模型</th>
                    <th>核心职责</th>
                    <th>KPI 数量</th>
                    <th>自动化任务</th>
                </tr>
                <tr>
                    <td>🤵 CEO 智能体</td>
                    <td>qwen3.5:397b</td>
                    <td>战略决策</td>
                    <td>4 个</td>
                    <td>6 个/天</td>
                </tr>
                <tr>
                    <td>📈 营销智能体</td>
                    <td>qwen3.5:35b</td>
                    <td>市场增长</td>
                    <td>6 个</td>
                    <td>7 个/天</td>
                </tr>
                <tr>
                    <td>⚙️ 运营智能体</td>
                    <td>qwen3.5:35b</td>
                    <td>业务执行</td>
                    <td>6 个</td>
                    <td>8 个/天</td>
                </tr>
                <tr>
                    <td>💰 财务智能体</td>
                    <td>qwen3.5:35b</td>
                    <td>资金管控</td>
                    <td>7 个</td>
                    <td>12 个/天</td>
                </tr>
                <tr>
                    <td>📊 数据智能体</td>
                    <td>qwen3.5:35b</td>
                    <td>数据分析</td>
                    <td>7 个</td>
                    <td>11 个/天</td>
                </tr>
                <tr>
                    <td>⚖️ 风控智能体</td>
                    <td>qwen3.5:35b</td>
                    <td>安全合规</td>
                    <td>7 个</td>
                    <td>11 个/天</td>
                </tr>
            </table>
        </div>
        
        <!-- 日常运营流程 -->
        <div class="section">
            <h2>🔄 日常运营流程 (24 小时)</h2>
            <div class="timeline">
                <div class="timeline-item">
                    <span class="timeline-time">06:00</span>
                    <p>📊 数据智能体采集夜间数据 (订单/设备/用户)</p>
                </div>
                <div class="timeline-item">
                    <span class="timeline-time">07:00</span>
                    <p>📝 各部门智能体生成日报 (营销/运营/财务/风控)</p>
                </div>
                <div class="timeline-item">
                    <span class="timeline-time">08:00</span>
                    <p>📊 数据智能体汇总分析，生成公司日报</p>
                </div>
                <div class="timeline-item">
                    <span class="timeline-time">09:00</span>
                    <p>🤵 CEO 智能体审阅日报，发出当日工作指令</p>
                </div>
                <div class="timeline-item">
                    <span class="timeline-time">09:30</span>
                    <p>⚡ 各智能体执行当日任务</p>
                </div>
                <div class="timeline-item">
                    <span class="timeline-time">12:00</span>
                    <p>⚖️ 风控智能体午间合规检查</p>
                </div>
                <div class="timeline-item">
                    <span class="timeline-time">18:00</span>
                    <p>📝 各部门生成晚报</p>
                </div>
                <div class="timeline-item">
                    <span class="timeline-time">20:00</span>
                    <p>🤵 CEO 智能体生成经营日报，发送管理层</p>
                </div>
                <div class="timeline-item">
                    <span class="timeline-time">22:00</span>
                    <p>💾 数据智能体备份归档</p>
                </div>
            </div>
        </div>
        
        <!-- KPI 仪表盘 -->
        <div class="section">
            <h2>📈 KPI 监控仪表盘</h2>
            <div class="kpi-grid">
                <div class="kpi-card">
                    <h3>🤵 CEO 智能体</h3>
                    <div class="kpi-item"><span>决策及时率</span><span class="kpi-value">98%</span></div>
                    <div class="kpi-item"><span>目标准确率</span><span class="kpi-value">92%</span></div>
                    <div class="kpi-item"><span>资源效率</span><span class="kpi-value">88%</span></div>
                    <div class="kpi-item"><span>风险识别率</span><span class="kpi-value">99%</span></div>
                </div>
                <div class="kpi-card">
                    <h3>📈 营销智能体</h3>
                    <div class="kpi-item"><span>新增用户</span><span class="kpi-value">≥1000/月</span></div>
                    <div class="kpi-item"><span>CAC</span><span class="kpi-value">≤¥50</span></div>
                    <div class="kpi-item"><span>ROI</span><span class="kpi-value">≥300%</span></div>
                    <div class="kpi-item"><span>留存率</span><span class="kpi-value">≥85%</span></div>
                </div>
                <div class="kpi-card">
                    <h3>⚙️ 运营智能体</h3>
                    <div class="kpi-item"><span>设备在线率</span><span class="kpi-value">≥98%</span></div>
                    <div class="kpi-item"><span>订单及时率</span><span class="kpi-value">≥99%</span></div>
                    <div class="kpi-item"><span>满意度</span><span class="kpi-value">≥4.5/5</span></div>
                    <div class="kpi-item"><span>故障率</span><span class="kpi-value">≤2%</span></div>
                </div>
                <div class="kpi-card">
                    <h3>💰 财务智能体</h3>
                    <div class="kpi-item"><span>现金流</span><span class="kpi-value">≥60 天</span></div>
                    <div class="kpi-item"><span>应收周转</span><span class="kpi-value">≤30 天</span></div>
                    <div class="kpi-item"><span>成本收入比</span><span class="kpi-value">≤70%</span></div>
                    <div class="kpi-item"><span>预算准确率</span><span class="kpi-value">≥95%</span></div>
                </div>
                <div class="kpi-card">
                    <h3>📊 数据智能体</h3>
                    <div class="kpi-item"><span>数据准确率</span><span class="kpi-value">≥99.9%</span></div>
                    <div class="kpi-item"><span>及时性</span><span class="kpi-value">≤5 分钟</span></div>
                    <div class="kpi-item"><span>预测准确率</span><span class="kpi-value">≥85%</span></div>
                    <div class="kpi-item"><span>管道可用性</span><span class="kpi-value">≥99.9%</span></div>
                </div>
                <div class="kpi-card">
                    <h3>⚖️ 风控智能体</h3>
                    <div class="kpi-item"><span>合规率</span><span class="kpi-value">100%</span></div>
                    <div class="kpi-item"><span>风险识别</span><span class="kpi-value">≥95%</span></div>
                    <div class="kpi-item"><span>响应时间</span><span class="kpi-value">≤1 小时</span></div>
                    <div class="kpi-item"><span>安全事故</span><span class="kpi-value">0</span></div>
                </div>
            </div>
        </div>
        
        <!-- 文件位置 -->
        <div class="section">
            <h2>📁 配置文件位置</h2>
            <pre>/root/.openclaw/workspace/projects/chargecloud-opc/
├── ai-management-plan.md         # 综合管理方案
├── architecture-diagram.md       # 架构流程图
├── agents/
│   ├── CONFIG_OVERVIEW.md        # 配置总览
│   ├── ceo_agent/config.yaml     # CEO 配置
│   ├── marketing_agent/config.yaml    # 营销配置
│   ├── operations_agent/config.yaml   # 运营配置
│   ├── finance_agent/config.yaml      # 财务配置
│   ├── data_agent/config.yaml         # 数据配置
│   └── risk_agent/config.yaml         # 风控配置
└── scripts/
    └── generate_architecture_diagrams.py  # 图生成脚本</pre>
        </div>
        
        <!-- 下一步行动 -->
        <div class="section">
            <h2>🚀 下一步行动</h2>
            <ol>
                <li><strong>审阅方案</strong> - 确认架构和配置是否符合需求</li>
                <li><strong>搭建框架</strong> - 部署智能体执行框架</li>
                <li><strong>配置任务</strong> - 设置定时任务和通信机制</li>
                <li><system>测试运行</strong> - 选择 1-2 个智能体先测试</li>
                <li><strong>全面部署</strong> - 6 大智能体全部上线</li>
            </ol>
        </div>
        
        <div class="footer">
            <p><strong>ChargeCloud OPC - AI 智能体管理系统</strong></p>
            <p>方案版本：v1.0 | 创建时间：2026-04-19 | 创建者：小智 (CEO 顾问智能体)</p>
            <p>有任何问题随时联系，我立刻调整！🚀</p>
        </div>
    </div>
</body>
</html>
"""

# 保存 HTML 文件
html_path = os.path.join(OUTPUT_DIR, 'architecture_email.html')
with open(html_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

print(f"✅ HTML 邮件已生成：{html_path}")
print(f"📧 下一步：发送到 19525456@qq.com")
