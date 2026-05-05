#!/usr/bin/env python3
"""发送 DeepSeek-v4-Flash × ComputeHub 私有化部署方案到邮箱"""

from scripts.email_utils import send_email_safe
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
import os

# ── 配置 ──
SMTP_SERVER = "smtp.qq.com"
SMTP_PORT = 587
FROM_EMAIL = "19525456@qq.com"
TO_EMAIL = "19525456@qq.com"
AUTH_CODE = "xunlwhjokescbgdd"

# ── 邮件正文 ──
TEXT_BODY = """DeepSeek-v4-Flash × ComputeHub 私有化部署方案
=====================================

一、核心目标
让 deepseek-v4-flash 模型跑在你自己的 GPU 机器上，
通过 ComputeHub 统一调度，OpenClaw 直接调用。

二、现有资产
  ✅ ComputeHub：14,698 行 Go 代码，Gateway/Worker/Scheduler/Dashboard 全可运行
  ✅ 编译好的二进制（ARM64）：
     - computehub-gateway  (8.3MB)
     - compute-worker     (8.0MB)
     - compute-node       (8.0MB)
     - computehub-tui     (8.2MB)
  ✅ OpenClaw 配置：ollama-cloud-2 provider 已有 deepseek-v4-flash 模型定义
  ✅ 1M 上下文窗口，reasoning=true — 已完整配置
  ❌ 本地无 GPU，Docker 不可用
  ❌ 已有的 192.168.1.7:11434 连接不上（内网隔离）

三、产品架构（数据流）

  小智（你） → OpenClaw Agent → ComputeHub Gateway(:8282)
       ↓
  ModelServer（新增模块）
    → POST /v1/chat/completions → 按负载/延迟选择最佳 GPU 节点
    → 转发到该节点的 Ollama API → deepseek-v4-flash 推理
    → 流式返回结果
       ↓
  同时：Worker Agent 每 10s 心跳上报 GPU 温度/利用率/显存
        Scheduler + 熔断器 保障服务稳定
        Dashboard 可视化全球算力地图

四、实施计划（3天）

  Day 1: 新增 compute-model-server 模块（~300行）
     - OpenAI 兼容 API：/v1/chat/completions, /v1/models
     - 智能分发：按负载/延迟/区域选择最优节点
     - 升级 Worker：自动启动 Ollama、拉模型、处理推理请求

  Day 2: 集成到 Gateway + OpenClaw
     - Gateway 新增 /v1/ 端点
     - OpenClaw 新增 "computehub" provider
     - 切换 primary：computehub/deepseek-v4-flash

  Day 3: 部署验证
     - 平板启动 Gateway
     - GPU 机器启动 Worker
     - 测试推理链路
     - Dashboard 确认节点在线

五、GPU 来源选项

  选项 A: 云 GPU（推荐首测，最快）
     Vast.ai / RunPod: $0.8-2.0/h
     租 1 台 H100 × 1 (80GB) → 装 Ollama → pull deepseek-v4-flash
     测试 24h 约 ¥150-200
     链路通了再决定长期方案

  选项 B: 已有服务器检查
     192.168.1.7 有 Ollama（当前连不上）
     192.168.2.165 Windows 机器
     需检查这些机器是否有 GPU

  选项 C: 实体卡自建（长期方案）
     RTX 4090 × 2 (48GB显存，量化可跑)
     成本约 ¥3-5 万
     Worker 常驻运行

六、今天能做的事

  # 1. 启动 ComputeHub Gateway
  cd projects/computehub
  ./code/bin/computehub-gateway &

  # 2. 验证节点管理 CLI
  ./code/bin/compute-node --gw http://192.168.1.17:8282 list

  # 3. 决定 GPU 来源后告诉我

七、产品化前景

  最终用户看到的界面：
    - 控制台：节点/模型/GPU利用率一目了然
    - 一键部署：任何 Ollama 模型，点一下部署
    - OpenAI 兼容 API：任何客户端直接用
    - 按 Token / 按时长计费

=====================================
生成时间：2026-05-04 06:58
"""

HTML_BODY = """
<html>
<head><meta charset="utf-8"></head>
<body style="font-family: -apple-system, 'Microsoft YaHei', sans-serif; max-width: 720px; margin: 0 auto; padding: 20px; color: #333;">
<div style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 30px; border-radius: 12px 12px 0 0;">
    <h1 style="margin: 0; font-size: 24px;">🚀 DeepSeek-v4-Flash × ComputeHub</h1>
    <p style="margin: 8px 0 0; opacity: 0.9;">私有化部署方案</p>
</div>

<div style="border: 1px solid #e0e0e0; border-top: none; padding: 25px; border-radius: 0 0 12px 12px;">

<h2 style="color: #5a67d8;">🎯 核心目标</h2>
<p>让 <strong>deepseek-v4-flash</strong> 模型跑在<strong>你自己的 GPU 机器</strong>上，通过 ComputeHub 统一调度，OpenClaw 直接调用。</p>

<h2 style="color: #5a67d8;">📦 现有资产</h2>
<table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
    <tr style="background: #f7fafc;">
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">✅ ComputeHub</td>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">14,698 行 Go 代码，全平台可运行</td>
    </tr>
    <tr>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">✅ 编译好的二进制</td>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">gateway / worker / node / tui 全就绪</td>
    </tr>
    <tr style="background: #f7fafc;">
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">✅ OpenClaw 配置</td>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">deepseek-v4-flash 模型定义已存在</td>
    </tr>
    <tr>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">❌ 本地 GPU</td>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">无独立显卡，需远程 GPU 节点</td>
    </tr>
</table>

<h2 style="color: #5a67d8;">🏗️ 架构数据流</h2>
<pre style="background: #1a202c; color: #a0f0a0; padding: 16px; border-radius: 8px; font-size: 13px; line-height: 1.6; overflow-x: auto;">
小智(你)
  → OpenClaw Agent (primary: computehub/deepseek-v4-flash)
    → ComputeHub Gateway (:8282)
      → ModelServer (/v1/chat/completions)
        → Scheduler(熔断器+负载均衡)
          → Worker Agent → Ollama → deepseek-v4-flash
  ← 流式推理结果返回
</pre>

<h2 style="color: #5a67d8;">📅 实施计划（3天）</h2>

<div style="background: #ebf4ff; padding: 12px 16px; border-radius: 8px; margin: 10px 0;">
    <strong>Day 1</strong> — 新增 compute-model-server 模块（~300行）<br>
    OpenAI 兼容 API + 智能分发 + Worker 升级
</div>
<div style="background: #f0fff4; padding: 12px 16px; border-radius: 8px; margin: 10px 0;">
    <strong>Day 2</strong> — 集成到 Gateway + OpenClaw<br>
    新增 /v1/ 端点 + computehub provider + 切换 primary
</div>
<div style="background: #fffaf0; padding: 12px 16px; border-radius: 8px; margin: 10px 0;">
    <strong>Day 3</strong> — 部署验证<br>
    Gateway 启动 → Worker 注册 → 推理测试 → Dashboard 确认
</div>

<h2 style="color: #5a67d8;">🖥️ GPU 选项</h2>
<table style="width: 100%; border-collapse: collapse; margin: 10px 0;">
    <tr style="background: #f7fafc;">
        <th style="padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left;">方案</th>
        <th style="padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left;">成本</th>
        <th style="padding: 8px 12px; border: 1px solid #e2e8f0; text-align: left;">说明</th>
    </tr>
    <tr>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">☁️ 云 GPU</td>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">¥150-200/天</td>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">Vast.ai H100，推荐首测</td>
    </tr>
    <tr style="background: #f7fafc;">
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">🏠 已有服务器</td>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">¥0</td>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">检查 192.168.1.7/2.165 是否有 GPU</td>
    </tr>
    <tr>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">🖥️ 实体卡</td>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">¥3-5 万</td>
        <td style="padding: 8px 12px; border: 1px solid #e2e8f0;">RTX 4090 × 2，长期方案</td>
    </tr>
</table>

<h2 style="color: #5a67d8;">🔧 今天能做的事</h2>
<pre style="background: #1a202c; color: #a0f0a0; padding: 16px; border-radius: 8px; font-size: 13px;">
# 启动 ComputeHub Gateway
cd projects/computehub
./code/bin/computehub-gateway &

# 验证节点管理 CLI
./code/bin/compute-node --gw http://192.168.1.17:8282 list

# 访问 Dashboard
# 浏览器打开 http://192.168.1.17:8282
</pre>

<h2 style="color: #5a67d8;">🌟 产品化前景</h2>
<p style="background: #f0fff4; padding: 12px; border-radius: 8px;">
最终用户看到的是一站式算力平台：<br>
<strong>控制台</strong> → 节点/模型/利用率一目了然<br>
<strong>一键部署</strong> → 任何 Ollama 模型点一下部署<br>
<strong>API</strong> → OpenAI 兼容，任意客户端直接用<br>
<strong>计费</strong> → 按 Token / 按时长灵活计费
</p>

<div style="border-top: 2px solid #e2e8f0; margin-top: 24px; padding-top: 16px; color: #718096; font-size: 12px;">
    生成时间：2026-05-04 06:58<br>
    生成者：小智 🤖
</div>
</div>
</body>
</html>
"""

def send():
    msg = MIMEMultipart("alternative")
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    msg["Subject"] = "📋 DeepSeek-v4-Flash × ComputeHub 私有化部署方案"

    msg.attach(MIMEText(TEXT_BODY, "plain", "utf-8"))
    msg.attach(MIMEText(HTML_BODY, "html", "utf-8"))

    # STARTTLS
    for server, port in [(SMTP_SERVER, 587), (SMTP_SERVER, 465)]:
        try:
            ctx = ssl.create_default_context()
            ctx.check_hostname = False
            ctx.verify_mode = ssl.CERT_NONE

            if port == 465:
                server_obj = smtplib.SMTP_SSL(server, port, timeout=15, context=ctx)
            else:
                server_obj = smtplib.SMTP(server, port, timeout=15)
                server_obj.ehlo()
                server_obj.starttls(context=ctx)
                server_obj.ehlo()

            server_obj.login(FROM_EMAIL, AUTH_CODE)
            server_obj.sendmail(FROM_EMAIL, [TO_EMAIL], msg.as_string())
            server_obj.quit()
            print(f"✅ 邮件发送成功！端口: {port}")
            print(f"📧 发送至: {TO_EMAIL}")
            print(f"📋 主题: DeepSeek-v4-Flash × ComputeHub 私有化部署方案")
            return True
        except Exception as e:
            print(f"  ⚠️ 端口 {port} 失败: {e}")
            continue

    print("❌ 所有端口都失败")
    return False

if __name__ == "__main__":
    send()


# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
