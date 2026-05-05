#!/usr/bin/env python3
"""
公司状态汇报邮件发送脚本
生成并发送完整的公司运营状态报告
"""

from scripts.email_utils import send_email_safe
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

def generate_html_report():
    """生成HTML格式的公司状态报告"""
    
    current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{
            font-family: 'Microsoft YaHei', 'PingFang SC', sans-serif;
            background: #f5f5f5;
            margin: 0;
            padding: 20px;
            color: #333;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            background: white;
            border-radius: 12px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            overflow: hidden;
        }}
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }}
        .header h1 {{
            margin: 0;
            font-size: 28px;
            font-weight: 600;
        }}
        .header p {{
            margin: 10px 0 0 0;
            opacity: 0.9;
        }}
        .content {{
            padding: 30px;
        }}
        .section {{
            margin-bottom: 30px;
        }}
        .section-title {{
            font-size: 18px;
            font-weight: 600;
            color: #667eea;
            border-bottom: 2px solid #667eea;
            padding-bottom: 10px;
            margin-bottom: 20px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin: 15px 0;
        }}
        th {{
            background: #f8f9fa;
            padding: 12px;
            text-align: left;
            font-weight: 600;
            color: #555;
            border-bottom: 2px solid #e9ecef;
        }}
        td {{
            padding: 12px;
            border-bottom: 1px solid #e9ecef;
        }}
        tr:hover {{
            background: #f8f9fa;
        }}
        .status-badge {{
            display: inline-block;
            padding: 4px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }}
        .status-green {{
            background: #d4edda;
            color: #155724;
        }}
        .status-yellow {{
            background: #fff3cd;
            color: #856404;
        }}
        .status-red {{
            background: #f8d7da;
            color: #721c24;
        }}
        .summary-grid {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 15px;
            margin: 20px 0;
        }}
        .summary-card {{
            background: #f8f9fa;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
        }}
        .summary-card .number {{
            font-size: 32px;
            font-weight: 700;
            color: #667eea;
        }}
        .summary-card .label {{
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }}
        .alert-box {{
            background: #fff3cd;
            border-left: 4px solid #ffc107;
            padding: 15px;
            margin: 15px 0;
            border-radius: 4px;
        }}
        .footer {{
            background: #f8f9fa;
            padding: 20px;
            text-align: center;
            color: #666;
            font-size: 14px;
        }}
        .progress-bar {{
            background: #e9ecef;
            border-radius: 10px;
            height: 8px;
            overflow: hidden;
        }}
        .progress-fill {{
            background: linear-gradient(90deg, #667eea, #764ba2);
            height: 100%;
            border-radius: 10px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>📊 公司运营状态报告</h1>
            <p>汇报时间：{current_time}</p>
        </div>
        
        <div class="content">
            <!-- 总体概况 -->
            <div class="section">
                <div class="section-title">📈 总体概况</div>
                <div class="summary-grid">
                    <div class="summary-card">
                        <div class="number">7</div>
                        <div class="label">总项目数</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">4</div>
                        <div class="label">活跃项目</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">16</div>
                        <div class="label">定时任务</div>
                    </div>
                    <div class="summary-card">
                        <div class="number">62.5%</div>
                        <div class="label">任务正常率</div>
                    </div>
                </div>
            </div>
            
            <!-- 项目状态 -->
            <div class="section">
                <div class="section-title">🏢 项目状态</div>
                <table>
                    <thead>
                        <tr>
                            <th>项目名称</th>
                            <th>状态</th>
                            <th>进度</th>
                            <th>备注</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>OpenRemoteAI</strong></td>
                            <td><span class="status-badge status-green">运行中</span></td>
                            <td>
                                <div class="progress-bar" style="width: 100px;">
                                    <div class="progress-fill" style="width: 90%;"></div>
                                </div>
                                90%
                            </td>
                            <td>开发完成，服务器+客户端就绪</td>
                        </tr>
                        <tr>
                            <td><strong>chargecloud-opc</strong></td>
                            <td><span class="status-badge status-green">已完成</span></td>
                            <td>
                                <div class="progress-bar" style="width: 100px;">
                                    <div class="progress-fill" style="width: 100%;"></div>
                                </div>
                                100%
                            </td>
                            <td>商业文档齐全，等待启动</td>
                        </tr>
                        <tr>
                            <td><strong>decision-viz-library</strong></td>
                            <td><span class="status-badge status-green">进行中</span></td>
                            <td>
                                <div class="progress-bar" style="width: 100px;">
                                    <div class="progress-fill" style="width: 70%;"></div>
                                </div>
                                70%
                            </td>
                            <td>决策可视化库开发</td>
                        </tr>
                        <tr>
                            <td><strong>stock-trading</strong></td>
                            <td><span class="status-badge status-green">运行中</span></td>
                            <td>
                                <div class="progress-bar" style="width: 100px;">
                                    <div class="progress-fill" style="width: 80%;"></div>
                                </div>
                                80%
                            </td>
                            <td>股票监控系统稳定运行</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <!-- 自动化系统 -->
            <div class="section">
                <div class="section-title">⚙️ 自动化系统状态</div>
                
                <h4 style="color: #28a745;">✅ 正常运行任务 (10个)</h4>
                <table>
                    <thead>
                        <tr>
                            <th>任务名称</th>
                            <th>执行频率</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>金融顾问学习</td>
                            <td>每2小时</td>
                            <td><span class="status-badge status-green">正常</span></td>
                        </tr>
                        <tr>
                            <td>财神爷财务分析</td>
                            <td>每小时</td>
                            <td><span class="status-badge status-green">正常</span></td>
                        </tr>
                        <tr>
                            <td>法海风险评估</td>
                            <td>每2小时</td>
                            <td><span class="status-badge status-green">正常</span></td>
                        </tr>
                        <tr>
                            <td>早间投资汇报</td>
                            <td>每天8:30</td>
                            <td><span class="status-badge status-green">正常</span></td>
                        </tr>
                        <tr>
                            <td>每日投资汇报</td>
                            <td>每天20:00</td>
                            <td><span class="status-badge status-green">正常</span></td>
                        </tr>
                        <tr>
                            <td>百炼用量日报</td>
                            <td>每天20:00</td>
                            <td><span class="status-badge status-green">正常</span></td>
                        </tr>
                        <tr>
                            <td>股票持仓提醒</td>
                            <td>工作日8:00</td>
                            <td><span class="status-badge status-green">正常</span></td>
                        </tr>
                        <tr>
                            <td>股票监控-盘前</td>
                            <td>工作日8:20</td>
                            <td><span class="status-badge status-green">正常</span></td>
                        </tr>
                        <tr>
                            <td>股票盘中监控</td>
                            <td>每20分钟</td>
                            <td><span class="status-badge status-green">正常</span></td>
                        </tr>
                        <tr>
                            <td>股票监控-集合竞价/开盘</td>
                            <td>多时段</td>
                            <td><span class="status-badge status-green">正常</span></td>
                        </tr>
                    </tbody>
                </table>
                
                <h4 style="color: #dc3545; margin-top: 20px;">⚠️ 异常任务 (3个)</h4>
                <div class="alert-box">
                    <strong>需要修复的问题：</strong><br>
                    1. 中远海发价格监控 - 连续57次错误（通道配置问题）<br>
                    2. system_pulse_10min - 连续32次错误（通道配置问题）<br>
                    3. 自动状态快照 - 连续16次错误（通道配置问题）<br><br>
                    <em>原因：isolated session任务未配置正确的delivery.channel</em>
                </div>
            </div>
            
            <!-- 股票持仓 -->
            <div class="section">
                <div class="section-title">📉 股票持仓监控</div>
                <table>
                    <thead>
                        <tr>
                            <th>股票</th>
                            <th>数量</th>
                            <th>成本价</th>
                            <th>当前价</th>
                            <th>盈亏</th>
                            <th>状态</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td><strong>华联股份 (000882)</strong></td>
                            <td>13,500股</td>
                            <td>¥1.873</td>
                            <td>¥1.66</td>
                            <td style="color: #dc3545; font-weight: 600;">-11.37%</td>
                            <td><span class="status-badge status-yellow">接近止损</span></td>
                        </tr>
                    </tbody>
                </table>
                <div class="alert-box">
                    <strong>⚠️ 风险提示：</strong>华联股份当前亏损-11.37%，距离止损位¥1.60仅差3.7%安全空间
                </div>
            </div>
            
            <!-- 系统评估 -->
            <div class="section">
                <div class="section-title">🎯 系统健康评估</div>
                <table>
                    <thead>
                        <tr>
                            <th>维度</th>
                            <th>状态</th>
                            <th>说明</th>
                        </tr>
                    </thead>
                    <tbody>
                        <tr>
                            <td>技术基础</td>
                            <td><span class="status-badge status-green">扎实</span></td>
                            <td>AI智能体框架运行稳定</td>
                        </tr>
                        <tr>
                            <td>运营系统</td>
                            <td><span class="status-badge status-green">良好</span></td>
                            <td>10个自动化任务正常运行</td>
                        </tr>
                        <tr>
                            <td>监控预警</td>
                            <td><span class="status-badge status-yellow">部分异常</span></td>
                            <td>3个任务需修复通道配置</td>
                        </tr>
                        <tr>
                            <td>商业转化</td>
                            <td><span class="status-badge status-yellow">待加强</span></td>
                            <td>技术项目多，商业化需推进</td>
                        </tr>
                    </tbody>
                </table>
            </div>
            
            <!-- 行动建议 -->
            <div class="section">
                <div class="section-title">💡 行动建议</div>
                <ol style="line-height: 2;">
                    <li><strong>高优先级：</strong>修复3个异常定时任务的通道配置问题</li>
                    <li><strong>中优先级：</strong>关注华联股份持仓，接近止损线</li>
                    <li><strong>长期规划：</strong>加强技术项目的商业化转化能力</li>
                </ol>
            </div>
        </div>
        
        <div class="footer">
            <p>发送者：小智 | AI智能体助手</p>
            <p>如有疑问，请在OpenClaw中联系小智</p>
        </div>
    </div>
</body>
</html>
"""
    return html

def send_email(to_addr, subject, html_content):
    """发送HTML邮件"""
    # 创建邮件
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_ACCOUNT
    msg['To'] = to_addr
    msg['Subject'] = subject
    
    # 添加HTML内容
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    # 发送邮件
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ACCOUNT, AUTH_CODE)
            server.sendmail(EMAIL_ACCOUNT, to_addr, msg.as_string())
        print(f"✅ 邮件发送成功！收件人：{to_addr}")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败：{e}")
        return False

if __name__ == "__main__":
    print("🤖 正在生成公司状态报告...")
    
    # 生成报告
    html_report = generate_html_report()
    
    # 主题
    subject = f"【公司状态报告】企业运营全景视图 - {datetime.now().strftime('%m月%d日')}"
    
    # 发送邮件
    print("📧 正在发送邮件...")
    success = send_email(TO_ADDR, subject, html_report)
    
    if success:
        print("\n✅ 公司状态报告已成功发送到邮箱：19525456@qq.com")
    else:
        print("\n❌ 发送失败，请检查网络或邮件配置")


# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
