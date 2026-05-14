#!/usr/bin/env python3
"""发送 ComputeHub v0.7.6 集群编译优化分析总结邮件"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import sys
import time

# 读取邮箱配置
CONFIG_PATH = "/root/.openclaw/workspace/config/email.conf"
config = {}
with open(CONFIG_PATH) as f:
    for line in f:
        line = line.strip()
        if '=' in line and not line.startswith('#'):
            k, v = line.split('=', 1)
            config[k.strip()] = v.strip()

SMTP_SERVER = config.get('SMTP_SERVER', 'smtp.qq.com')
SMTP_PORT = int(config.get('SMTP_PORT', 465))
SENDER_EMAIL = config.get('EMAIL', '')
EMAIL_PASS = config.get('AUTH_CODE', '')
RECEIVER_EMAIL = "19525456@qq.com"

def send_email():
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = "【ComputeHub v0.7.6】集群编译优化分析总结 - 2026-05-13"

    body = """
<html>
<body style="font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif; color: #333; line-height: 1.8;">

<h1>🔬 ComputeHub 集群编译 — 代码级优化分析</h1>
<p><strong>日期</strong>: 2026-05-13 &nbsp;|&nbsp; <strong>版本</strong>: v0.7.6 (15/15 ✅) &nbsp;|&nbsp; <strong>方式</strong>: 基于源码深度分析</p>
<hr>

<h2>1. 🔴 P0：输出流式回写</h2>
<p><strong>现状</strong>: <code>executor.go</code> 使用 <code>exec.Command("sh", "-c", command).CombinedOutput()</code> 同步执行，所有 stdout/stderr 被吞掉，只有最后 exit code 和 duration。编译 20 分钟，TUI/用户中间毫无反馈。</p>
<p><strong>已有基础设施</strong>: <code>handleTaskProgress</code> 接口和 <code>UpdateTaskStream()</code> 已实现，但 Worker 执行器没有 goroutine 实时推送。</p>
<p><strong>优化方向</strong>: 执行时启动 goroutine，扫描 stdout pipe 实时推送到 Gateway 的 TaskStream。</p>
<p><strong>收益</strong>: TUI 可实时看到 <code>[02/15] gateway → linux-amd64 ✅ (8.8MB)</code></p>

<h2>2. 🔴 P0：任务命令路径硬编码</h2>
<p><strong>现状</strong>: 编译提交的任务命令写死了完整路径 <code>cd /root/.openclaw/workspace/projects/computehub && bash scripts/build_all.sh</code>。前两次编译失败就是因为路径不对。不同节点的项目路径完全不同，<strong>任务不可移植</strong>。</p>
<p><strong>优化方向</strong>: TaskSubmit 增加结构化的 action 字段（compile/deploy/run），Worker 根据 Action 自动组装命令。</p>
<p><strong>收益</strong>: 任务可移植，不同节点/项目无需写完整路径</p>

<h2>3. 🔴 P0：离线节点告警</h2>
<p><strong>现状</strong>: <code>StartHealthMonitor(15s)</code> 已启动，心跳超时判定已有。但调度器 <code>findPendingTaskForNode()</code> 没有先检查节点在线状态。termux/proot 网络层断开时任务在队列里空转。</p>
<p><strong>优化方向</strong>: 调度前快速过滤 offline 节点，无可用节点时立即返回错误告警。</p>
<p><strong>收益</strong>: 离线时 API 立即返回错误，TUI 显示红色告警</p>

<h2>4. 🟡 P1：任务状态机不完整</h2>
<p><strong>现状</strong>: <code>LocalTaskRunner</code> 执行完命令后没有正确更新 TaskState 为 completed/failed，API 查出来还是 running（<strong>幽灵状态</strong>）。</p>
<p><strong>优化方向</strong>: 执行完成后立即更新状态 + 清理残留 goroutine</p>
<p><strong>收益</strong>: 状态准确，避免幽灵状态</p>

<h2>5. 🟡 P1：产物管理分散</h2>
<p><strong>现状</strong>: 编译产物散落在 <code>bin/</code>（本地）、<code>deploy/0.7.6/</code>（版本归档）、<code>sha256sums.txt</code>（校验和），没有自动打包成 tar.gz。</p>
<p><strong>优化方向</strong>: 编译任务 PostBuild 阶段自动打包 + 上传 + 通知</p>
<p><strong>收益</strong>: 一次提交 → 编译 → 打包 → 推送 全自动</p>

<h2>6. 🟡 P1：Worker 无安全限制</h2>
<p><strong>现状</strong>: <code>exec.Command("sh", "-c", command)</code> 执行任意命令，无 CPU/内存限制、无执行超时硬截断、可任意文件读写。</p>
<p><strong>优化方向</strong>: cgroup v2 限制资源 + 硬超时 kill</p>

<h2>7. 🟢 P2：调度策略太简单</h2>
<p><strong>现状</strong>: <code>findPendingTaskForNode()</code> 只是遍历找第一个有 pending 任务的节点，不考虑平台亲和性、节点负载、距离/延迟。</p>
<p><strong>优化方向</strong>: 加权评分 — platform_match × 0.5 + load × 0.3 + region × 0.2</p>

<hr>

<h2>📊 优化优先级总结</h2>
<table style="border-collapse: collapse; width: 100%; margin: 20px 0;">
<thead>
<tr style="background: #f0f0f0;">
<th style="border: 1px solid #ddd; padding: 10px; text-align: left;">优先级</th>
<th style="border: 1px solid #ddd; padding: 10px; text-align: left;">问题</th>
<th style="border: 1px solid #ddd; padding: 10px; text-align: left;">改动范围</th>
<th style="border: 1px solid #ddd; padding: 10px; text-align: left;">预期收益</th>
</tr>
</thead>
<tbody>
<tr><td style="border: 1px solid #ddd; padding: 10px; color: red; font-weight: bold;">P0</td><td style="border: 1px solid #ddd; padding: 10px;">输出流式回写</td><td style="border: 1px solid #ddd; padding: 10px;">executor.go</td><td style="border: 1px solid #ddd; padding: 10px;">🟢🟢🟢 体验质变</td></tr>
<tr><td style="border: 1px solid #ddd; padding: 10px; color: red; font-weight: bold;">P0</td><td style="border: 1px solid #ddd; padding: 10px;">离线节点告警</td><td style="border: 1px solid #ddd; padding: 10px;">gateway_worker.go</td><td style="border: 1px solid #ddd; padding: 10px;">🟢🟢🟢 运维可见</td></tr>
<tr><td style="border: 1px solid #ddd; padding: 10px; color: red; font-weight: bold;">P0</td><td style="border: 1px solid #ddd; padding: 10px;">任务状态修复</td><td style="border: 1px solid #ddd; padding: 10px;">LocalTaskRunner</td><td style="border: 1px solid #ddd; padding: 10px;">🟢🟢 准确状态</td></tr>
<tr><td style="border: 1px solid #ddd; padding: 10px; color: orange; font-weight: bold;">P1</td><td style="border: 1px solid #ddd; padding: 10px;">Action/WorkingDir 抽象</td><td style="border: 1px solid #ddd; padding: 10px;">TaskSubmit + Worker</td><td style="border: 1px solid #ddd; padding: 10px;">🟢🟢 可移植</td></tr>
<tr><td style="border: 1px solid #ddd; padding: 10px; color: orange; font-weight: bold;">P1</td><td style="border: 1px solid #ddd; padding: 10px;">产物自动打包</td><td style="border: 1px solid #ddd; padding: 10px;">build_all.sh 后处理</td><td style="border: 1px solid #ddd; padding: 10px;">🟢🟢 自动化</td></tr>
<tr><td style="border: 1px solid #ddd; padding: 10px; color: orange; font-weight: bold;">P1</td><td style="border: 1px solid #ddd; padding: 10px;">执行安全限制</td><td style="border: 1px solid #ddd; padding: 10px;">executor.go</td><td style="border: 1px solid #ddd; padding: 10px;">🟢 安全</td></tr>
<tr><td style="border: 1px solid #ddd; padding: 10px; color: green; font-weight: bold;">P2</td><td style="border: 1px solid #ddd; padding: 10px;">调度策略增强</td><td style="border: 1px solid #ddd; padding: 10px;">Scheduler</td><td style="border: 1px solid #ddd; padding: 10px;">🟢 性能</td></tr>
</tbody>
</table>

<hr>
<p style="color: #999; font-size: 12px;">— 小智 AI 助手 | 2026-05-13 09:16</p>

</body>
</html>
"""

    msg.attach(MIMEText(body, 'html', 'utf-8'))

    try:
        print(f"📧 发送邮件 → {RECEIVER_EMAIL}")
        if SMTP_PORT == 465:
            server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, timeout=30)
        else:
            server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=30)
            server.starttls()

        server.login(SENDER_EMAIL, EMAIL_PASS)
        server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        server.quit()
        print("✅ 邮件发送成功！")
        return True
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

if __name__ == '__main__':
    if not EMAIL_PASS:
        print("❌ 请配置邮箱授权码")
        sys.exit(1)
    send_email()
