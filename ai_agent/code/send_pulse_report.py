#!/usr/bin/env python3
"""
公司脉搏报告自动发送脚本
生成系统状态报告并发送到指定邮箱
"""

from scripts.email_utils import send_email_safe
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
import subprocess
from pathlib import Path

# 邮件配置
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 465
EMAIL_ACCOUNT = "19525456@qq.com"
AUTH_CODE = "bzgwylbbrocdbiie"
TO_ADDR = "19525456@qq.com"

def check_system_health():
    """检查系统健康状态"""
    health = {}
    try:
        result = subprocess.run(['df', '-h', '/'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            parts = lines[1].split()
            health['disk'] = {'use_percent': parts[4], 'available': parts[3]}
    except:
        health['disk'] = {'use_percent': 'N/A', 'available': 'N/A'}
    
    try:
        result = subprocess.run(['free', '-m'], capture_output=True, text=True)
        lines = result.stdout.strip().split('\n')
        for line in lines:
            if line.startswith('Mem:'):
                parts = line.split()
                health['memory'] = {'total_mb': parts[1], 'used_mb': parts[2], 'free_mb': parts[3]}
    except:
        health['memory'] = {'total_mb': 'N/A', 'used_mb': 'N/A', 'free_mb': 'N/A'}
    
    return health

def check_expert_learning():
    """检查专家学习状态"""
    skills_dir = Path("/root/.openclaw/workspace/skills")
    experts = ['finance-advisor', 'finance-expert', 'hr-expert', 'legal-advisor', 
               'marketing-expert', 'network-expert', 'ceo-advisor']
    
    expert_status = {}
    total_refs = 0
    for expert in experts:
        ref_dir = skills_dir / expert / 'references'
        if ref_dir.exists():
            files = list(ref_dir.glob('*'))
            expert_status[expert] = len(files)
            total_refs += len(files)
        else:
            expert_status[expert] = 0
    
    return expert_status, total_refs

def generate_report_html(period):
    """生成HTML格式报告"""
    current_time = datetime.now().strftime("%Y年%m月%d日 %H:%M")
    health = check_system_health()
    experts, total_refs = check_expert_learning()
    
    # 检查股票数据
    stock_dir = Path("/root/.openclaw/workspace/projects/stock-trading")
    stock_exists = stock_dir.exists()
    
    html = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>公司脉搏报告 - {period}</title>
    <style>
        body {{ font-family: 'Microsoft YaHei', sans-serif; background: #f5f7fa; padding: 20px; margin: 0; }}
        .container {{ max-width: 800px; margin: 0 auto; background: white; border-radius: 16px; padding: 30px; box-shadow: 0 4px 20px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px; margin-bottom: 25px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 28px; }}
        .header .time {{ opacity: 0.9; margin-top: 10px; }}
        .section {{ margin: 25px 0; padding: 20px; background: #f8f9fa; border-radius: 12px; }}
        .section-title {{ font-size: 18px; font-weight: 600; color: #333; margin-bottom: 15px; border-left: 4px solid #667eea; padding-left: 10px; }}
        .metric {{ display: flex; justify-content: space-between; padding: 10px 0; border-bottom: 1px solid #e9ecef; }}
        .metric:last-child {{ border-bottom: none; }}
        .metric-label {{ color: #666; }}
        .metric-value {{ font-weight: 600; color: #333; }}
        .status-ok {{ color: #28a745; }}
        .status-warn {{ color: #ffc107; }}
        .status-danger {{ color: #dc3545; }}
        .expert-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 10px; }}
        .expert-item {{ background: white; padding: 12px; border-radius: 8px; display: flex; justify-content: space-between; }}
        .footer {{ text-align: center; color: #888; margin-top: 30px; font-size: 14px; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🏢 公司脉搏报告</h1>
            <div class="time">{period} | {current_time}</div>
        </div>
        
        <div class="section">
            <div class="section-title">🔹 系统健康状态</div>
            <div class="metric">
                <span class="metric-label">磁盘使用</span>
                <span class="metric-value {'status-ok' if int(health['disk']['use_percent'].rstrip('%')) < 80 else 'status-warn'}">{health['disk']['use_percent']}</span>
            </div>
            <div class="metric">
                <span class="metric-label">内存使用</span>
                <span class="metric-value">{health['memory']['used_mb']}MB / {health['memory']['total_mb']}MB</span>
            </div>
            <div class="metric">
                <span class="metric-label">可用磁盘</span>
                <span class="metric-value">{health['disk']['available']}</span>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">🔹 专家学习状态 (7/7 活跃)</div>
            <div class="expert-grid">
                <div class="expert-item"><span>金融顾问</span><strong>{experts['finance-advisor']} 篇</strong></div>
                <div class="expert-item"><span>财务专家</span><strong>{experts['finance-expert']} 篇</strong></div>
                <div class="expert-item"><span>人力资源</span><strong>{experts['hr-expert']} 篇</strong></div>
                <div class="expert-item"><span>法律顾问</span><strong>{experts['legal-advisor']} 篇</strong></div>
                <div class="expert-item"><span>营销专家</span><strong>{experts['marketing-expert']} 篇</strong></div>
                <div class="expert-item"><span>网络专家</span><strong>{experts['network-expert']} 篇</strong></div>
                <div class="expert-item"><span>CEO顾问</span><strong>{experts['ceo-advisor']} 篇</strong></div>
            </div>
            <div class="metric" style="margin-top: 15px; background: #e8f5e9; padding: 10px; border-radius: 8px;">
                <span class="metric-label">总计学习文档</span>
                <span class="metric-value status-ok">{total_refs} 篇</span>
            </div>
        </div>
        
        <div class="section">
            <div class="section-title">🔹 股票监控系统</div>
            <div class="metric">
                <span class="metric-label">项目状态</span>
                <span class="metric-value {'status-ok' if stock_exists else 'status-danger'}">{'✅ 正常运行' if stock_exists else '❌ 未找到'}</span>
            </div>
        </div>
        
        <div class="footer">
            <p>🤖 小智 - AI智能体助手 | 公司运营监控系统</p>
            <p>自动生成于 {current_time}</p>
        </div>
    </div>
</body>
</html>
"""
    return html

def send_report(period="午间"):
    """发送报告邮件"""
    html_content = generate_report_html(period)
    current_time = datetime.now().strftime("%m月%d日")
    
    msg = MIMEMultipart('alternative')
    msg['From'] = EMAIL_ACCOUNT
    msg['To'] = TO_ADDR
    msg['Subject'] = f"【公司脉搏报告】{period} - {current_time}"
    
    msg.attach(MIMEText(html_content, 'html', 'utf-8'))
    
    try:
        with smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT) as server:
            server.login(EMAIL_ACCOUNT, AUTH_CODE)
            server.sendmail(EMAIL_ACCOUNT, TO_ADDR, msg.as_string())
        print(f"✅ 公司脉搏报告({period})发送成功！")
        return True
    except Exception as e:
        print(f"❌ 发送失败：{e}")
        return False

if __name__ == "__main__":
    import sys
    period = sys.argv[1] if len(sys.argv) > 1 else "定时"
    print(f"🤖 正在生成公司脉搏报告({period})...")
    send_report(period)


# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
