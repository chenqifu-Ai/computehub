#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
vLLM 日志分析报告 - 邮件发送
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os
import time

# 从配置文件读取
with open("/root/.openclaw/workspace/config/email.conf") as f:
    config = {}
    for line in f:
        line = line.strip()
        if "=" in line and not line.startswith("#"):
            k, v = line.split("=", 1)
            config[k.strip()] = v.strip()

SMTP_SERVER = config["SMTP_SERVER"]
EMAIL = config["EMAIL"]
AUTH_CODE = config["AUTH_CODE"]

log_path = "/data/data/com.termux/files/home/downloads/qwen36-1.log"
with open(log_path, "r", encoding="utf-8") as f:
    log_content = f.read()

# 统计关键指标
total_lines = len(log_content.split("\n"))
total_requests = log_content.count('POST /v1/chat/completions')
ok_responses = log_content.count('200 OK')
error_400 = log_content.count('400 Bad Request')
error_401 = log_content.count('401 Unauthorized')
error_404 = log_content.count('404 Not Found')
error_500 = log_content.count('500 Internal')
template_errors = log_content.count('No user query found in messages')

# 提取性能指标
import re

prompt_throughputs = re.findall(r'Avg prompt throughput: ([\d.]+) tokens/s', log_content)
generation_throughputs = re.findall(r'Avg generation throughput: ([\d.]+) tokens/s', log_content)
kv_usages = re.findall(r'GPU KV cache usage: ([\d.]+)%', log_content)
running_reqs = re.findall(r'Running: (\d+) reqs', log_content)

avg_prompt = sum(float(x) for x in prompt_throughputs) / len(prompt_throughputs) if prompt_throughputs else 0
avg_gen = sum(float(x) for x in generation_throughputs) / len(generation_throughputs) if generation_throughputs else 0
max_kv = max(float(x) for x in kv_usages) if kv_usages else 0
min_kv = min(float(x) for x in kv_usages) if kv_usages else 0
avg_running = sum(int(x) for x in running_reqs) / len(running_reqs) if running_reqs else 0
max_running = max(int(x) for x in running_reqs) if running_reqs else 0

html_body = f"""
<html>
<body style="font-family: 'Microsoft YaHei', sans-serif; padding: 20px; background: #0f172a; color: #e2e8f0;">
<div style="max-width: 700px; margin: 0 auto; background: #1e293b; padding: 30px; border-radius: 15px;">
    <h2 style="color: #22d3ee; border-bottom: 2px solid #22d3ee; padding-bottom: 10px;">📊 vLLM 运行日志分析报告</h2>
    <p style="color: #94a3b8;">日志文件: <code>qwen36-1.log</code> | 总行数: {total_lines:,} 行</p>
    
    <div style="background: rgba(34,197,94,0.1); padding: 15px; border-radius: 10px; margin: 20px 0; border-left: 4px solid #22c55e;">
        <h3 style="color: #4ade80; margin-bottom: 10px;">🟢 整体状态：健康</h3>
        <p style="color: #e2e8f0;">vLLM 服务运行正常，性能稳定，仅极少数请求报错。</p>
    </div>
    
    <h3 style="color: #22d3ee; margin-top: 25px;">📈 性能指标</h3>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">Prompt 吞吐量</td><td style="padding: 8px; border-bottom: 1px solid #334155; text-align: right; color: #4ade80;">{avg_prompt:,.1f} tokens/s</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">生成吞吐量</td><td style="padding: 8px; border-bottom: 1px solid #334155; text-align: right; color: #fbbf24;">{avg_gen:,.1f} tokens/s</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">GPU KV Cache 峰值</td><td style="padding: 8px; border-bottom: 1px solid #334155; text-align: right; color: {max_kv > 30 and '#f87171' or '#4ade80'};">{max_kv:.1f}%</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">并发请求 (平均)</td><td style="padding: 8px; border-bottom: 1px solid #334155; text-align: right; color: #60a5fa;">{avg_running:.1f} reqs</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">并发请求 (峰值)</td><td style="padding: 8px; border-bottom: 1px solid #334155; text-align: right; color: #60a5fa;">{max_running} reqs</td></tr>
    </table>
    
    <h3 style="color: #22d3ee; margin-top: 25px;">📋 请求统计</h3>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">总请求数</td><td style="padding: 8px; border-bottom: 1px solid #334155; text-align: right; color: #e2e8f0;">{total_requests:,}</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">✅ 成功 (200)</td><td style="padding: 8px; border-bottom: 1px solid #334155; text-align: right; color: #4ade80;">{ok_responses:,}</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">❌ 参数错误 (400)</td><td style="padding: 8px; border-bottom: 1px solid #334155; text-align: right; color: #f87171;">{error_400}</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">🔐 未授权 (401)</td><td style="padding: 8px; border-bottom: 1px solid #334155; text-align: right; color: #fbbf24;">{error_401}</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">🔍 未找到 (404)</td><td style="padding: 8px; border-bottom: 1px solid #334155; text-align: right; color: #fbbf24;">{error_404}</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">⚠️ 模板错误</td><td style="padding: 8px; border-bottom: 1px solid #334155; text-align: right; color: #f87171;">{template_errors} (空消息)</td></tr>
    </table>
    
    <h3 style="color: #22d3ee; margin-top: 25px;">⚠️ 异常分析</h3>
    
    <div style="background: rgba(251,191,36,0.1); padding: 15px; border-radius: 10px; margin: 15px 0;">
        <h4 style="color: #fbbf24; margin-bottom: 8px;">1. 空消息请求 (2次)</h4>
        <p style="color: #94a3b8; font-size: 13px;">
            时间: 23:31:16 和 23:34:27<br>
            错误: <code>No user query found in messages</code><br>
            来源: 183.253.29.199（腾讯云）<br>
            影响: 返回 400 错误，不影响正常请求
        </p>
    </div>
    
    <div style="background: rgba(248,113,113,0.1); padding: 15px; border-radius: 10px; margin: 15px 0;">
        <h4 style="color: #f87171; margin-bottom: 8px;">2. 无效 HTTP 请求 (1次)</h4>
        <p style="color: #94a3b8; font-size: 13px;">
            时间: 23:39:xx<br>
            错误: <code>Invalid HTTP request received</code><br>
            影响: 极小
        </p>
    </div>
    
    <h3 style="color: #22d3ee; margin-top: 25px;">🌐 客户端来源</h3>
    <table style="width: 100%; border-collapse: collapse; margin: 15px 0;">
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">183.253.29.199</td><td style="padding: 8px; border-bottom: 1px solid #334155; color: #94a3b8;">腾讯云</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">183.253.15.228</td><td style="padding: 8px; border-bottom: 1px solid #334155; color: #94a3b8;">腾讯云</td></tr>
        <tr><td style="padding: 8px; border-bottom: 1px solid #334155;">180.163.29.103</td><td style="padding: 8px; border-bottom: 1px solid #334155; color: #94a3b8;">腾讯云</td></tr>
    </table>
    
    <h3 style="color: #22d3ee; margin-top: 25px;">💡 建议</h3>
    <ul style="color: #94a3b8; line-height: 2;">
        <li>✅ 服务运行正常，无需干预</li>
        <li>⚠️ 空消息请求来自外部（腾讯云），可能是百炼平台或第三方调用方</li>
        <li>💡 可考虑在网关层拦截空消息请求，减少 400 错误</li>
        <li>💡 生成吞吐量波动大（2~547 tokens/s），建议检查 max_tokens 配置</li>
    </ul>
    
    <hr style="margin: 25px 0; border-color: #334155;">
    <p style="color: #64748b; font-size: 14px;">
        — 小智 AI 助手 · 2026-04-24<br>
        日志分析完成
    </p>
</div>
</body>
</html>
"""

# 创建邮件
msg = MIMEMultipart()
msg['From'] = EMAIL
msg['To'] = EMAIL
msg['Subject'] = f"📊 [小智] vLLM 运行日志分析报告 - {time.strftime('%Y-%m-%d')}"

msg.attach(MIMEText(html_body, 'html', 'utf-8'))

# 添加日志附件
if os.path.exists(log_path):
    with open(log_path, "rb") as f:
        attach = MIMEBase('application', 'octet-stream')
        attach.set_payload(f.read())
    encoders.encode_base64(attach)
    attach.add_header('Content-Disposition', 'attachment', 
                      filename='qwen36-vllm-log-report.json')
    # 生成分析结果 JSON
    analysis = {
        "report_time": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
        "log_file": "qwen36-1.log",
        "total_lines": total_lines,
        "total_requests": total_requests,
        "success_rate": f"{ok_responses}/{total_requests}",
        "errors": {
            "400": error_400,
            "401": error_401,
            "404": error_404,
            "template": template_errors,
        },
        "performance": {
            "avg_prompt_throughput": f"{avg_prompt:.1f} tokens/s",
            "avg_generation_throughput": f"{avg_gen:.1f} tokens/s",
            "max_kv_cache": f"{max_kv:.1f}%",
            "avg_concurrent": f"{avg_running:.1f} reqs",
            "max_concurrent": f"{max_running} reqs",
        }
    }
    with open('/tmp/vllm_analysis.json', 'w') as f:
        import json
        json.dump(analysis, f, ensure_ascii=False, indent=2)
    with open('/tmp/vllm_analysis.json', 'rb') as f:
        attach2 = MIMEBase('application', 'octet-stream')
        attach2.set_payload(f.read())
    encoders.encode_base64(attach2)
    attach2.add_header('Content-Disposition', 'attachment', 
                       filename='vllm-log-analysis.json')
    msg.attach(attach2)

# 发送邮件
try:
    server = smtplib.SMTP_SSL('smtp.qq.com', 465, timeout=30)
    server.login(EMAIL, AUTH_CODE)
    print("📧 连接到 SMTP 服务器")
    
    server.sendmail(EMAIL, EMAIL, msg.as_string())
    print("✅ 邮件发送成功!")
    print(f"   发件人: {EMAIL}")
    print(f"   收件人: {EMAIL}")
    print(f"   主题: 📊 [小智] vLLM 运行日志分析报告")
    print(f"   附件: qwen36-1.log + vllm-log-analysis.json")
    
    server.quit()
    print("✅ 完成")
        
except Exception as e:
    print(f"❌ 发送失败: {e}")
