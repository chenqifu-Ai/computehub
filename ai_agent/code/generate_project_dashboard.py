#!/usr/bin/env python3
"""
公司项目仪表盘生成器
生成完整的项目仪表盘并发送邮件
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import os

# 邮件配置
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
EMAIL_ACCOUNT = "19525456@qq.com"
AUTH_CODE = "xunlwhjokescbgdd"
TO_ADDR = "19525456@qq.com"

def generate_dashboard_html():
    """生成项目仪表盘HTML"""
    
    current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>公司项目仪表盘</title>
    <style>
        :root {{
            --primary: #667eea;
            --secondary: #764ba2;
            --success: #28a745;
            --warning: #ffc107;
            --danger: #dc3545;
            --info: #17a2b8;
            --dark: #343a40;
            --light: #f8f9fa;
        }}
        
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', -apple-system, BlinkMacSystemFont, sans-serif;
            background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
            min-height: 100vh;
            padding: 20px;
            color: #333;
        }}
        
        .container {{
            max-width: 1400px;
            margin: 0 auto;
        }}
        
        /* 头部样式 */
        .header {{
            background: linear-gradient(135deg, var(--primary) 0%, var(--secondary) 100%);
            color: white;
            padding: 40px;
            border-radius: 20px;
            margin-bottom: 30px;
            box-shadow: 0 10px 40px rgba(102, 126, 234, 0.3);
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: -50%;
            right: -10%;
            width: 500px;
            height: 500px;
            background: rgba(255,255,255,0.1);
            border-radius: 50%;
        }}
        
        .header h1 {{
            font-size: 36px;
            font-weight: 700;
            margin-bottom: 10px;
            position: relative;
        }}
        
        .header .subtitle {{
            opacity: 0.9;
            font-size: 16px;
            position: relative;
        }}
        
        .header .update-time {{
            position: absolute;
            bottom: 20px;
            right: 40px;
            opacity: 0.8;
            font-size: 14px;
        }}
        
        /* 统计卡片 */
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .stat-card {{
            background: white;
            border-radius: 16px;
            padding: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            transition: transform 0.3s ease, box-shadow 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .stat-card:hover {{
            transform: translateY(-5px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }}
        
        .stat-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
        }}
        
        .stat-card.total::before {{ background: var(--primary); }}
        .stat-card.active::before {{ background: var(--success); }}
        .stat-card.completed::before {{ background: var(--info); }}
        .stat-card.alert::before {{ background: var(--danger); }}
        
        .stat-card .icon {{
            width: 60px;
            height: 60px;
            border-radius: 12px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 28px;
            margin-bottom: 15px;
        }}
        
        .stat-card.total .icon {{ background: rgba(102, 126, 234, 0.1); color: var(--primary); }}
        .stat-card.active .icon {{ background: rgba(40, 167, 69, 0.1); color: var(--success); }}
        .stat-card.completed .icon {{ background: rgba(23, 162, 184, 0.1); color: var(--info); }}
        .stat-card.alert .icon {{ background: rgba(220, 53, 69, 0.1); color: var(--danger); }}
        
        .stat-card .number {{
            font-size: 42px;
            font-weight: 700;
            margin-bottom: 5px;
        }}
        
        .stat-card.total .number {{ color: var(--primary); }}
        .stat-card.active .number {{ color: var(--success); }}
        .stat-card.completed .number {{ color: var(--info); }}
        .stat-card.alert .number {{ color: var(--danger); }}
        
        .stat-card .label {{
            color: #666;
            font-size: 14px;
        }}
        
        /* 项目卡片 */
        .section-title {{
            font-size: 24px;
            font-weight: 600;
            margin: 40px 0 20px 0;
            display: flex;
            align-items: center;
            gap: 10px;
        }}
        
        .projects-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 25px;
        }}
        
        .project-card {{
            background: white;
            border-radius: 16px;
            padding: 25px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .project-card:hover {{
            transform: translateY(-3px);
            box-shadow: 0 8px 30px rgba(0,0,0,0.12);
        }}
        
        .project-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 15px;
        }}
        
        .project-title {{
            font-size: 20px;
            font-weight: 600;
            color: #333;
        }}
        
        .status-badge {{
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
        }}
        
        .status-running {{ background: rgba(40, 167, 69, 0.1); color: var(--success); }}
        .status-completed {{ background: rgba(23, 162, 184, 0.1); color: var(--info); }}
        .status-progress {{ background: rgba(255, 193, 7, 0.1); color: #856404; }}
        .status-pending {{ background: rgba(108, 117, 125, 0.1); color: #6c757d; }}
        
        .project-desc {{
            color: #666;
            font-size: 14px;
            margin-bottom: 20px;
            line-height: 1.6;
        }}
        
        .progress-section {{
            margin-bottom: 20px;
        }}
        
        .progress-header {{
            display: flex;
            justify-content: space-between;
            margin-bottom: 8px;
            font-size: 14px;
        }}
        
        .progress-bar {{
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
        }}
        
        .progress-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.5s ease;
        }}
        
        .progress-fill.green {{ background: linear-gradient(90deg, #28a745, #20c997); }}
        .progress-fill.blue {{ background: linear-gradient(90deg, #17a2b8, #0dcaf0); }}
        .progress-fill.yellow {{ background: linear-gradient(90deg, #ffc107, #ffca2c); }}
        .progress-fill.purple {{ background: linear-gradient(90deg, #6f42c1, #8b5cf6); }}
        
        .project-meta {{
            display: flex;
            gap: 20px;
            font-size: 13px;
            color: #888;
            padding-top: 15px;
            border-top: 1px solid #e9ecef;
        }}
        
        .project-meta span {{
            display: flex;
            align-items: center;
            gap: 5px;
        }}
        
        /* 自动化任务表格 */
        .tasks-section {{
            background: white;
            border-radius: 16px;
            padding: 30px;
            margin-top: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        
        .tasks-table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
        }}
        
        .tasks-table th {{
            background: #f8f9fa;
            padding: 15px;
            text-align: left;
            font-weight: 600;
            color: #555;
            border-bottom: 2px solid #e9ecef;
        }}
        
        .tasks-table td {{
            padding: 15px;
            border-bottom: 1px solid #e9ecef;
        }}
        
        .tasks-table tr:hover {{
            background: #f8f9fa;
        }}
        
        .task-status {{
            display: inline-block;
            width: 10px;
            height: 10px;
            border-radius: 50%;
            margin-right: 8px;
        }}
        
        .task-status.ok {{ background: var(--success); }}
        .task-status.error {{ background: var(--danger); }}
        
        /* 股票监控 */
        .stock-section {{
            background: white;
            border-radius: 16px;
            padding: 30px;
            margin-top: 30px;
            box-shadow: 0 4px 20px rgba(0,0,0,0.08);
        }}
        
        .stock-card {{
            background: linear-gradient(135deg, #f8f9fa 0%, #e9ecef 100%);
            border-radius: 12px;
            padding: 20px;
            margin-top: 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}
        
        .stock-info h3 {{
            font-size: 18px;
            margin-bottom: 10px;
        }}
        
        .stock-price {{
            font-size: 32px;
            font-weight: 700;
            color: var(--danger);
        }}
        
        .stock-change {{
            font-size: 16px;
            color: var(--danger);
            margin-top: 5px;
        }}
        
        /* 页脚 */
        .footer {{
            text-align: center;
            padding: 30px;
            color: #888;
            font-size: 14px;
            margin-top: 40px;
        }}
        
        /* 响应式 */
        @media (max-width: 768px) {{
            .projects-grid {{
                grid-template-columns: 1fr;
            }}
            
            .stats-grid {{
                grid-template-columns: repeat(2, 1fr);
            }}
            
            .header h1 {{
                font-size: 28px;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- 头部 -->
        <div class="header">
            <h1>🏢 公司项目仪表盘</h1>
            <div class="subtitle">AI智能体项目全景监控系统</div>
            <div class="update-time">更新时间：{current_time}</div>
        </div>
        
        <!-- 统计卡片 -->
        <div class="stats-grid">
            <div class="stat-card total">
                <div class="icon">📊</div>
                <div class="number">7</div>
                <div class="label">总项目数</div>
            </div>
            <div class="stat-card active">
                <div class="icon">🚀</div>
                <div class="number">4</div>
                <div class="label">活跃运行</div>
            </div>
            <div class="stat-card completed">
                <div class="icon">✅</div>
                <div class="number">2</div>
                <div class="label">已完成</div>
            </div>
            <div class="stat-card alert">
                <div class="icon">⚠️</div>
                <div class="number">0</div>
                <div class="label">异常任务</div>
            </div>
        </div>
        
        <!-- 项目列表 -->
        <div class="section-title">📁 项目列表</div>
        
        <div class="projects-grid">
            <!-- OpenRemoteAI -->
            <div class="project-card">
                <div class="project-header">
                    <div class="project-title">🌐 OpenRemoteAI</div>
                    <span class="status-badge status-running">运行中</span>
                </div>
                <div class="project-desc">
                    AI驱动远程连接优化系统，服务器+客户端已就绪，准备部署
                </div>
                <div class="progress-section">
                    <div class="progress-header">
                        <span>完成进度</span>
                        <span style="color: #28a745; font-weight: 600;">90%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill green" style="width: 90%;"></div>
                    </div>
                </div>
                <div class="project-meta">
                    <span>📅 创建时间: 2026-03-27</span>
                    <span>👤 负责人: 小智</span>
                </div>
            </div>
            
            <!-- ChargeCloud -->
            <div class="project-card">
                <div class="project-header">
                    <div class="project-title">⚡ ChargeCloud</div>
                    <span class="status-badge status-completed">已完成</span>
                </div>
                <div class="project-desc">
                    充电桩运营管理SaaS平台，商业文档齐全，等待开发启动
                </div>
                <div class="progress-section">
                    <div class="progress-header">
                        <span>完成进度</span>
                        <span style="color: #17a2b8; font-weight: 600;">100%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill blue" style="width: 100%;"></div>
                    </div>
                </div>
                <div class="project-meta">
                    <span>📅 创建时间: 2026-03-21</span>
                    <span>📋 文档: 12份</span>
                </div>
            </div>
            
            <!-- DecisionViz -->
            <div class="project-card">
                <div class="project-header">
                    <div class="project-title">📊 DecisionViz</div>
                    <span class="status-badge status-progress">进行中</span>
                </div>
                <div class="project-desc">
                    决策可视化库，支持复杂数据的图表展示和决策分析
                </div>
                <div class="progress-section">
                    <div class="progress-header">
                        <span>完成进度</span>
                        <span style="color: #856404; font-weight: 600;">70%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill yellow" style="width: 70%;"></div>
                    </div>
                </div>
                <div class="project-meta">
                    <span>📅 创建时间: 2026-03-29</span>
                    <span>🛠️ 类型: 技术库</span>
                </div>
            </div>
            
            <!-- StockTrading -->
            <div class="project-card">
                <div class="project-header">
                    <div class="project-title">📈 StockTrading</div>
                    <span class="status-badge status-running">运行中</span>
                </div>
                <div class="project-desc">
                    股票交易监控系统，实时监控持仓价格，自动发送预警通知
                </div>
                <div class="progress-section">
                    <div class="progress-header">
                        <span>完成进度</span>
                        <span style="color: #6f42c1; font-weight: 600;">80%</span>
                    </div>
                    <div class="progress-bar">
                        <div class="progress-fill purple" style="width: 80%;"></div>
                    </div>
                </div>
                <div class="project-meta">
                    <span>📅 创建时间: 2026-03-23</span>
                    <span>🔔 状态: 监控中</span>
                </div>
            </div>
        </div>
        
        <!-- 自动化任务 -->
        <div class="tasks-section">
            <div class="section-title">⚙️ 自动化任务监控</div>
            
            <table class="tasks-table">
                <thead>
                    <tr>
                        <th>任务名称</th>
                        <th>执行频率</th>
                        <th>状态</th>
                        <th>下次执行</th>
                    </tr>
                </thead>
                <tbody>
                    <tr>
                        <td><span class="task-status ok"></span>金融顾问学习</td>
                        <td>每2小时</td>
                        <td><span style="color: #28a745;">✅ 正常</span></td>
                        <td>07:07</td>
                    </tr>
                    <tr>
                        <td><span class="task-status ok"></span>法海风险评估</td>
                        <td>每2小时</td>
                        <td><span style="color: #28a745;">✅ 正常</span></td>
                        <td>09:09</td>
                    </tr>
                    <tr>
                        <td><span class="task-status ok"></span>股票盘中监控</td>
                        <td>每20分钟</td>
                        <td><span style="color: #28a745;">✅ 正常</span></td>
                        <td>09:20</td>
                    </tr>
                    <tr>
                        <td><span class="task-status ok"></span>早间投资汇报</td>
                        <td>每天8:30</td>
                        <td><span style="color: #28a745;">✅ 正常</span></td>
                        <td>明天8:30</td>
                    </tr>
                    <tr>
                        <td><span class="task-status ok"></span>每日投资汇报</td>
                        <td>每天20:00</td>
                        <td><span style="color: #28a745;">✅ 正常</span></td>
                        <td>今天20:00</td>
                    </tr>
                    <tr>
                        <td><span class="task-status ok"></span>system_pulse_10min</td>
                        <td>每10分钟</td>
                        <td><span style="color: #28a745;">✅ 已修复</span></td>
                        <td>07:10</td>
                    </tr>
                    <tr>
                        <td><span class="task-status ok"></span>中远海发价格监控</td>
                        <td>每30分钟</td>
                        <td><span style="color: #28a745;">✅ 已修复</span></td>
                        <td>07:35</td>
                    </tr>
                    <tr>
                        <td><span class="task-status ok"></span>自动状态快照</td>
                        <td>每小时</td>
                        <td><span style="color: #28a745;">✅ 已修复</span></td>
                        <td>08:05</td>
                    </tr>
                </tbody>
            </table>
        </div>
        
        <!-- 股票持仓 -->
        <div class="stock-section">
            <div class="section-title">📉 股票持仓监控</div>
            
            <div class="stock-card">
                <div class="stock-info">
                    <h3>华联股份 (000882)</h3>
                    <div style="color: #666; font-size: 14px;">持仓: 13,500股 | 成本: ¥1.873</div>
                </div>
                <div style="text-align: right;">
                    <div class="stock-price">¥1.66</div>
                    <div class="stock-change">📉 -11.37% (-¥2,875.50)</div>
                    <div style="margin-top: 10px; padding: 5px 12px; background: #fff3cd; border-radius: 6px; font-size: 13px; color: #856404;">
                        ⚠️ 接近止损线 ¥1.60
                    </div>
                </div>
            </div>
        </div>
        
        <!-- 页脚 -->
        <div class="footer">
            <p>🤖 小智 - AI智能体助手 | 公司运营监控系统</p>
            <p style="margin-top: 10px; opacity: 0.8;">更新时间：{current_time}</p>
        </div>
    </div>
</body>
</html>
"""
    return html

def send_dashboard_email():
    """发送仪表盘邮件"""
    html_content = generate_dashboard_html()
    
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_ACCOUNT
    msg['To'] = TO_ADDR
    msg['Subject'] = f"【公司仪表盘】项目全景监控 - {datetime.now().strftime('%m月%d日 %H:%M')}"
    
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ACCOUNT, AUTH_CODE)
            server.sendmail(EMAIL_ACCOUNT, TO_ADDR, msg.as_string())
        print(f"✅ 仪表盘邮件发送成功！")
        return True
    except Exception as e:
        print(f"❌ 发送失败：{e}")
        return False

if __name__ == "__main__":
    print("🤖 正在生成公司项目仪表盘...")
    send_dashboard_email()
