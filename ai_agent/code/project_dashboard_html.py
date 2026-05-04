#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HTML项目状态表盘展示
生成交互式HTML表盘界面
"""

import json
from datetime import datetime

def generate_html_dashboard():
    """生成HTML格式的表盘展示"""
    
    # 项目数据
    projects = [
        {
            "name": "AI智能体框架开发",
            "priority": "P0",
            "status": "🟢 85%完成",
            "progress": 85,
            "category": "技术基石",
            "description": "公司技术基础",
            "color": "success"
        },
        {
            "name": "专家知识系统建设",
            "priority": "P0",
            "status": "🟢 84%完成",
            "progress": 84,
            "category": "技术基石",
            "description": "核心竞争力",
            "color": "success"
        },
        {
            "name": "Stream运营系统",
            "priority": "P1",
            "status": "🟢 100%完成",
            "progress": 100,
            "category": "运营基础",
            "description": "自主运行能力",
            "color": "success"
        },
        {
            "name": "监控预警系统优化",
            "priority": "P1",
            "status": "🟡 70%完成",
            "progress": 70,
            "category": "运营基础",
            "description": "风险控制保障",
            "color": "warning"
        },
        {
            "name": "投资管理服务Demo",
            "priority": "P2",
            "status": "🟢 80%完成",
            "progress": 80,
            "category": "商业验证",
            "description": "技术验证案例",
            "color": "success"
        },
        {
            "name": "连续流技能研发",
            "priority": "P2",
            "status": "🟡 50%完成",
            "progress": 50,
            "category": "商业验证",
            "description": "技术创新探索",
            "color": "warning"
        },
        {
            "name": "OpenRemoteAI项目",
            "priority": "P3",
            "status": "🔴 被遗漏",
            "progress": 0,
            "category": "商业转化",
            "description": "急需重启",
            "color": "danger"
        },
        {
            "name": "企业AI咨询服务",
            "priority": "P3",
            "status": "🟡 10%规划",
            "progress": 10,
            "category": "商业转化",
            "description": "商业收入来源",
            "color": "danger"
        }
    ]
    
    # 股票信息
    stocks = [
        {
            "name": "华联股份",
            "code": "000882",
            "quantity": "13,500股",
            "cost_price": "¥1.873",
            "current_price": "¥1.66",
            "profit_loss": "-11.37% (-¥2,875.50)",
            "status": "接近止损",
            "color": "danger"
        },
        {
            "name": "中远海发",
            "code": "601866",
            "status": "关注中",
            "current_price": "¥2.78",
            "buy_range": "¥2.50-2.70",
            "color": "info"
        }
    ]
    
    # 系统状态
    systems = [
        {"name": "OpenClaw", "status": "运行中", "color": "success"},
        {"name": "Ollama Cloud", "status": "正常", "color": "success"},
        {"name": "邮件系统", "status": "正常", "color": "success"},
        {"name": "监控系统", "status": "优化中", "color": "warning"}
    ]
    
    # 生成HTML
    html = f"""
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>项目状态表盘 - {datetime.now().strftime('%Y-%m-%d %H:%M')}</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            padding: 20px;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        
        .header {{
            text-align: center;
            color: white;
            margin-bottom: 30px;
        }}
        
        .header h1 {{
            font-size: 2.5em;
            margin-bottom: 10px;
            text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        }}
        
        .header .subtitle {{
            font-size: 1.2em;
            opacity: 0.9;
        }}
        
        .dashboard-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(350px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        
        .card {{
            background: white;
            border-radius: 15px;
            padding: 25px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: transform 0.3s ease;
        }}
        
        .card:hover {{
            transform: translateY(-5px);
        }}
        
        .card h2 {{
            color: #333;
            margin-bottom: 20px;
            font-size: 1.5em;
            border-bottom: 2px solid #eee;
            padding-bottom: 10px;
        }}
        
        .project-item {{
            margin-bottom: 20px;
            padding: 15px;
            border-radius: 10px;
            background: #f8f9fa;
        }}
        
        .project-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 10px;
        }}
        
        .priority {{
            padding: 4px 12px;
            border-radius: 20px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        
        .priority-p0 {{ background: #ff6b6b; color: white; }}
        .priority-p1 {{ background: #4ecdc4; color: white; }}
        .priority-p2 {{ background: #45b7d1; color: white; }}
        .priority-p3 {{ background: #96ceb4; color: white; }}
        
        .progress-bar {{
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            margin: 10px 0;
        }}
        
        .progress-fill {{
            height: 100%;
            border-radius: 4px;
            transition: width 0.3s ease;
        }}
        
        .progress-success {{ background: #28a745; }}
        .progress-warning {{ background: #ffc107; }}
        .progress-danger {{ background: #dc3545; }}
        
        .status-badge {{
            padding: 4px 8px;
            border-radius: 12px;
            font-size: 0.8em;
            font-weight: bold;
        }}
        
        .status-success {{ background: #d4edda; color: #155724; }}
        .status-warning {{ background: #fff3cd; color: #856404; }}
        .status-danger {{ background: #f8d7da; color: #721c24; }}
        .status-info {{ background: #d1ecf1; color: #0c5460; }}
        
        .stock-item {{
            padding: 15px;
            margin-bottom: 15px;
            border-radius: 10px;
            background: #f8f9fa;
        }}
        
        .system-item {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 10px 0;
            border-bottom: 1px solid #eee;
        }}
        
        .stats-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 15px;
            margin-top: 20px;
        }}
        
        .stat-card {{
            text-align: center;
            padding: 20px;
            background: #f8f9fa;
            border-radius: 10px;
        }}
        
        .stat-number {{
            font-size: 2em;
            font-weight: bold;
            color: #333;
        }}
        
        .stat-label {{
            color: #666;
            margin-top: 5px;
        }}
        
        @media (max-width: 768px) {{
            .dashboard-grid {{
                grid-template-columns: 1fr;
            }}
            
            .header h1 {{
                font-size: 2em;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 项目状态表盘</h1>
            <p class="subtitle">更新时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
        </div>
        
        <div class="dashboard-grid">
            <!-- 项目状态 -->
            <div class="card">
                <h2>🎯 项目状态</h2>
                {''.join([f'''
                <div class="project-item">
                    <div class="project-header">
                        <span class="priority priority-{project['priority'].lower()}">{project['priority']}</span>
                        <span class="status-{project['color']}">{project['status']}</span>
                    </div>
                    <h3>{project['name']}</h3>
                    <p style="color: #666; font-size: 0.9em; margin: 5px 0;">📍 {project['category']} | 📝 {project['description']}</p>
                    <div class="progress-bar">
                        <div class="progress-fill progress-{project['color']}" style="width: {project['progress']}%"></div>
                    </div>
                    <div style="text-align: right; font-size: 0.9em; color: #666;">{project['progress']}% 完成</div>
                </div>
                ''' for project in projects])}
            </div>
            
            <!-- 股票状态 -->
            <div class="card">
                <h2>📈 股票持仓</h2>
                {''.join([f'''
                <div class="stock-item">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 10px;">
                        <h3>{stock['name']}({stock['code']})</h3>
                        <span class="status-{stock['color']}">{stock['status']}</span>
                    </div>
                    {'<p>📊 持仓: ' + stock['quantity'] + ' | 成本: ' + stock['cost_price'] + '</p>' if 'quantity' in stock else ''}
                    <p>💰 现价: {stock['current_price']} {'| 盈亏: ' + stock['profit_loss'] if 'profit_loss' in stock else '| 买入区间: ' + stock['buy_range']}</p>
                </div>
                ''' for stock in stocks])}
            </div>
            
            <!-- 系统状态 -->
            <div class="card">
                <h2>⚙️ 系统状态</h2>
                {''.join([f'''
                <div class="system-item">
                    <span>{system['name']}</span>
                    <span class="status-{system['color']}">{system['status']}</span>
                </div>
                ''' for system in systems])}
            </div>
        </div>
        
        <!-- 统计信息 -->
        <div class="card">
            <h2>📊 项目统计</h2>
            <div class="stats-grid">
                <div class="stat-card">
                    <div class="stat-number">{len(projects)}</div>
                    <div class="stat-label">总项目数</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len([p for p in projects if p['progress'] >= 90])}</div>
                    <div class="stat-label">已完成</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{len([p for p in projects if 20 <= p['progress'] < 90])}</div>
                    <div class="stat-label">进行中</div>
                </div>
                <div class="stat-card">
                    <div class="stat-number">{int(sum(p['progress'] for p in projects) / len(projects))}%</div>
                    <div class="stat-label">整体进度</div>
                </div>
            </div>
        </div>
    </div>
    
    <script>
        // 简单的动画效果
        document.addEventListener('DOMContentLoaded', function() {{
            const progressBars = document.querySelectorAll('.progress-fill');
            progressBars.forEach(bar => {{
                const width = bar.style.width;
                bar.style.width = '0%';
                setTimeout(() => {{
                    bar.style.width = width;
                }}, 100);
            }});
        }});
    </script>
</body>
</html>
"""
    
    return html

if __name__ == "__main__":
    try:
        html_content = generate_html_dashboard()
        
        # 保存HTML文件
        with open("/root/.openclaw/workspace/ai_agent/results/project_dashboard.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        print("✅ HTML表盘已生成: /root/.openclaw/workspace/ai_agent/results/project_dashboard.html")
        print("📊 可以在浏览器中打开查看交互式表盘")
        
        # 同时生成简化的文本版本
        with open("/root/.openclaw/workspace/ai_agent/results/project_dashboard_simple.txt", "w", encoding="utf-8") as f:
            f.write(f"项目状态表盘 - {datetime.now().strftime('%Y-%m-%d %H:%M')}\n")
            f.write("="*50 + "\n")
            
            # 项目状态
            f.write("🎯 项目状态:\n")
            for project in [
                {"name": "AI智能体框架开发", "progress": 85, "status": "🟢"},
                {"name": "专家知识系统建设", "progress": 84, "status": "🟢"},
                {"name": "Stream运营系统", "progress": 100, "status": "🟢"},
                {"name": "监控预警系统优化", "progress": 70, "status": "🟡"},
                {"name": "投资管理服务Demo", "progress": 80, "status": "🟢"},
                {"name": "连续流技能研发", "progress": 50, "status": "🟡"},
                {"name": "OpenRemoteAI项目", "progress": 0, "status": "🔴"},
                {"name": "企业AI咨询服务", "progress": 10, "status": "🔴"}
            ]:
                bar = "█" * (project['progress'] // 10) + "░" * (10 - project['progress'] // 10)
                f.write(f"{project['status']} [{bar}] {project['name']} ({project['progress']}%)\n")
            
            f.write("\n📈 股票持仓:\n")
            f.write("⚠️ 华联股份(000882): ¥1.66 (-11.37%)\n")
            f.write("👀 中远海发(601866): ¥2.78 (关注中)\n")
            
            f.write("\n⚙️ 系统状态:\n")
            f.write("🟢 OpenClaw: 运行中\n")
            f.write("🟢 Ollama Cloud: 正常\n")
            f.write("🟢 邮件系统: 正常\n")
            f.write("🟡 监控系统: 优化中\n")
        
        print("✅ 简化版表盘已保存: /root/.openclaw/workspace/ai_agent/results/project_dashboard_simple.txt")
        
    except Exception as e:
        print(f"❌ 生成HTML表盘时出错: {e}")