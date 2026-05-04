#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
发送今天的超详细百炼 API 用量报告（带时间戳）
包含：任务分类、时间分布、工具使用、费用分析、每次调用时间戳
"""

import smtplib
import json
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import date, datetime
from pathlib import Path
from collections import defaultdict

# 配置
EMAIL_CONFIG = {
    "smtp_server": "smtp.qq.com",
    "smtp_port": 465,
    "from_email": "19525456@qq.com",
    "to_email": "19525456@qq.com",
    "password": "xunlwhjokescbgdd"
}

today = date.today().isoformat()

# 分析日志提取任务详情
def analyze_session_logs():
    """分析会话日志，提取每个任务的详情"""
    tasks = []
    
    session_dir = Path.home() / ".openclaw" / "agents" / "main" / "sessions"
    
    for session_file in session_dir.glob("*.jsonl"):
        with open(session_file, 'r', encoding='utf-8') as f:
            for line in f:
                try:
                    data = json.loads(line)
                    if data.get("type") == "message" and data.get("message", {}).get("role") == "assistant":
                        timestamp_str = data.get("timestamp", "")
                        if isinstance(timestamp_str, str) and timestamp_str.startswith(today):
                            # 提取小时和完整时间
                            hour = int(timestamp_str[11:13]) if len(timestamp_str) > 13 else 0
                            # 格式化时间戳：09:46:23
                            time_only = timestamp_str[11:19] if len(timestamp_str) > 19 else ""
                            
                            content = data.get("message", {}).get("content", [])
                            
                            task_type = "unknown"
                            tool_calls = []
                            text_content = ""
                            tool_args = {}
                            
                            for item in content:
                                if isinstance(item, dict):
                                    if item.get("type") == "toolCall":
                                        tool_name = item.get("name", "")
                                        tool_calls.append(tool_name)
                                        tool_args = item.get("arguments", {})
                                        
                                        if "memory_search" in tool_name:
                                            task_type = "记忆搜索"
                                        elif "read" in tool_name:
                                            task_type = "文件读取"
                                        elif "exec" in tool_name:
                                            task_type = "命令执行"
                                        elif "cron" in tool_name:
                                            task_type = "定时任务管理"
                                        elif "session_status" in tool_name:
                                            task_type = "状态检查"
                                        elif "write" in tool_name:
                                            task_type = "文件写入"
                                        elif "edit" in tool_name:
                                            task_type = "文件编辑"
                                    elif item.get("type") == "text":
                                        text_content = item.get("text", "")
                            
                            if not tool_calls and text_content:
                                if "HEARTBEAT_OK" in text_content:
                                    task_type = "心跳响应"
                                elif "NO_REPLY" in text_content:
                                    task_type = "静默响应"
                                elif "reply_to" in text_content:
                                    task_type = "对话回复"
                            
                            if task_type == "unknown" and tool_calls:
                                task_type = "工具调用"
                            
                            tasks.append({
                                "timestamp": timestamp_str,
                                "time": time_only,
                                "hour": hour,
                                "type": task_type,
                                "tools": tool_calls,
                                "tool_args": tool_args,
                                "text_preview": text_content[:150] if text_content else "",
                                "text_length": len(text_content)
                            })
                except:
                    continue
    
    return tasks

# 统计任务
tasks_list = analyze_session_logs()

# 按类型分组统计
task_stats = defaultdict(lambda: {"count": 0, "tools": [], "descriptions": [], "hours": [], "timestamps": []})

for task in tasks_list:
    task_type = task["type"]
    task_stats[task_type]["count"] += 1
    if task["tools"]:
        task_stats[task_type]["tools"].extend(task["tools"])
    if task["text_preview"]:
        task_stats[task_type]["descriptions"].append(task["text_preview"][:50])
    task_stats[task_type]["hours"].append(task["hour"])
    task_stats[task_type]["timestamps"].append(task["time"])

# 估算 tokens
token_estimates = {
    "对话回复": {"input": 800, "output": 400},
    "记忆搜索": {"input": 600, "output": 200},
    "文件读取": {"input": 500, "output": 150},
    "命令执行": {"input": 400, "output": 800},
    "定时任务管理": {"input": 500, "output": 600},
    "状态检查": {"input": 300, "output": 100},
    "文件写入": {"input": 600, "output": 200},
    "文件编辑": {"input": 700, "output": 150},
    "心跳响应": {"input": 400, "output": 50},
    "静默响应": {"input": 400, "output": 30},
    "工具调用": {"input": 500, "output": 300},
    "unknown": {"input": 500, "output": 300}
}

# 计算总 tokens 和详细统计
total_input = 0
total_output = 0
detailed_tasks = []

for task_type, stats in task_stats.items():
    estimate = token_estimates.get(task_type, token_estimates["unknown"])
    input_tokens = estimate["input"] * stats["count"]
    output_tokens = estimate["output"] * stats["count"]
    total_tokens = input_tokens + output_tokens
    
    total_input += input_tokens
    total_output += output_tokens
    
    # 计算小时分布
    hour_dist = defaultdict(int)
    for h in stats["hours"]:
        hour_dist[h] += 1
    
    detailed_tasks.append({
        "type": task_type,
        "count": stats["count"],
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "avg_input": estimate["input"],
        "avg_output": estimate["output"],
        "tools_used": list(set(stats["tools"]))[:5],
        "sample": stats["descriptions"][0] if stats["descriptions"] else "",
        "hour_distribution": dict(sorted(hour_dist.items())),
        "timestamps": stats["timestamps"]  # 每次调用的时间戳
    })

# 按 tokens 降序排序
detailed_tasks.sort(key=lambda x: x["total_tokens"], reverse=True)

# 小时统计
hour_stats = defaultdict(lambda: {"calls": 0, "tokens": 0})
for task in tasks_list:
    hour = task["hour"]
    hour_stats[hour]["calls"] += 1
    estimate = token_estimates.get(task["type"], token_estimates["unknown"])
    hour_stats[hour]["tokens"] += estimate["input"] + estimate["output"]

# 找出高峰时段
peak_hour = max(hour_stats.items(), key=lambda x: x[1]["calls"]) if hour_stats else (0, {"calls": 0})

report = {
    "date": today,
    "total_calls": len(tasks_list),
    "total_input": total_input,
    "total_output": total_output,
    "total_tokens": total_input + total_output,
    "detailed_tasks": detailed_tasks,
    "hour_stats": dict(sorted(hour_stats.items())),
    "peak_hour": peak_hour[0],
    "peak_calls": peak_hour[1]["calls"] if isinstance(peak_hour, tuple) else 0,
    "all_timestamps": [(t["time"], t["type"]) for t in tasks_list]  # 所有调用的时间戳
}

# 估算费用
input_cost = total_input * 0.002 / 1000
output_cost = total_output * 0.006 / 1000
total_cost = input_cost + output_cost

# 平均每 call tokens
avg_tokens = report["total_tokens"] // report["total_calls"] if report["total_calls"] > 0 else 0

# 构建邮件
subject = f"📊 百炼 API 用量超详细日报（带时间戳） - {report['date']}"

# 生成任务详情 HTML
tasks_html = ""
for i, task in enumerate(detailed_tasks, 1):
    tools_str = ", ".join(task["tools_used"]) if task["tools_used"] else "-"
    sample_str = task["sample"][:60] + "..." if task["sample"] else "-"
    row_color = "#f9f9f9" if i % 2 == 0 else "#ffffff"
    
    # 小时分布
    hour_dist_str = " ".join([f"{h}点:{c}次" for h, c in task["hour_distribution"].items()])
    
    # 时间戳列表（前 10 个）
    timestamps_str = ", ".join(task["timestamps"][:10])
    if len(task["timestamps"]) > 10:
        timestamps_str += f" ... 等{len(task['timestamps'])}次"
    
    tasks_html += f"""
        <tr style="background-color: {row_color};">
            <td>{i}</td>
            <td><strong>{task['type']}</strong></td>
            <td>{task['count']} 次</td>
            <td>{task['input_tokens']:,}</td>
            <td>{task['output_tokens']:,}</td>
            <td><strong>{task['total_tokens']:,}</strong></td>
            <td>{task['avg_input']}/{task['avg_output']}</td>
            <td style="font-size: 12px; color: #666;">{tools_str}</td>
            <td style="font-size: 11px; color: #999;">{hour_dist_str}</td>
            <td style="font-size: 11px; color: #999;">{timestamps_str}</td>
            <td style="font-size: 12px; color: #999;">{sample_str}</td>
        </tr>
        """

# 小时分布 HTML
hour_html = ""
for hour in range(24):
    if hour in hour_stats:
        stats = hour_stats[hour]
        bar_width = (stats["calls"] / max(h["calls"] for h in hour_stats.values())) * 100 if hour_stats else 0
        hour_html += f"""
            <tr>
                <td>{hour:02d}:00</td>
                <td>{stats['calls']} 次</td>
                <td>{stats['tokens']:,}</td>
                <td>
                    <div style="background-color: #e0e0e0; width: 100%; height: 20px; border-radius: 3px;">
                        <div style="background-color: #3498db; width: {bar_width}%; height: 100%; border-radius: 3px;"></div>
                    </div>
                </td>
            </tr>
        """

# 时间戳明细 HTML（按时间排序）
timestamp_detail_html = ""
sorted_timestamps = sorted(report["all_timestamps"], key=lambda x: x[0])
for i, (time, task_type) in enumerate(sorted_timestamps, 1):
    row_color = "#f9f9f9" if i % 2 == 0 else "#ffffff"
    timestamp_detail_html += f"""
        <tr style="background-color: {row_color};">
            <td>{i}</td>
            <td><strong>{time}</strong></td>
            <td>{task_type}</td>
        </tr>
        """

html_content = f"""
<html>
<body style="font-family: 'Segoe UI', Arial, sans-serif; line-height: 1.6; color: #333;">
    <div style="max-width: 1100px; margin: 0 auto; padding: 20px;">
        <h2 style="color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px;">📊 百炼 API 用量超详细日报（带时间戳）</h2>
        <p><strong>📅 日期:</strong> {report['date']}</p>
        <p style="color: #666; font-size: 14px;">⚠️ 注：这是首份超详细报告，tokens 为估算值。从明天开始会精确记录每次调用。</p>
        
        <h3 style="color: #2c3e50; background-color: #ecf0f1; padding: 8px;">📈 核心指标</h3>
        <table border="1" cellpadding="12" cellspacing="0" style="border-collapse: collapse; width: 100%; margin-bottom: 20px;">
            <tr style="background-color: #3498db; color: white;">
                <th>指标</th>
                <th>数值</th>
                <th>说明</th>
            </tr>
            <tr>
                <td>📞 总调用次数</td>
                <td><strong>{report['total_calls']} 次</strong></td>
                <td>今日 API 调用总数</td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td>📥 输入 Tokens</td>
                <td>{report['total_input']:,}</td>
                <td>发送给模型的 tokens</td>
            </tr>
            <tr>
                <td>📤 输出 Tokens</td>
                <td>{report['total_output']:,}</td>
                <td>模型返回的 tokens</td>
            </tr>
            <tr style="background-color: #e8f4fd;">
                <td>📊 总 Tokens 消耗</td>
                <td><strong>{report['total_tokens']:,}</strong></td>
                <td>输入 + 输出</td>
            </tr>
            <tr>
                <td>📈 平均每次调用</td>
                <td><strong>{avg_tokens:,} tokens</strong></td>
                <td>总 tokens / 总调用</td>
            </tr>
            <tr style="background-color: #fff3cd;">
                <td>💰 估算费用</td>
                <td><strong>¥{total_cost:.4f}</strong></td>
                <td>输入¥0.002/千，输出¥0.006/千</td>
            </tr>
            <tr>
                <td>🕐 高峰时段</td>
                <td><strong>{report['peak_hour']:02d}:00</strong></td>
                <td>{report['peak_calls']} 次调用</td>
            </tr>
            <tr style="background-color: #f9f9f9;">
                <td>📋 任务类型数</td>
                <td><strong>{len(detailed_tasks)} 类</strong></td>
                <td>不同任务类型的数量</td>
            </tr>
        </table>
        
        <h3 style="color: #2c3e50; background-color: #ecf0f1; padding: 8px;">📋 任务详情（按 Tokens 消耗排序）</h3>
        <table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 11px;">
            <tr style="background-color: #3498db; color: white;">
                <th>#</th>
                <th>任务类型</th>
                <th>调用次数</th>
                <th>输入</th>
                <th>输出</th>
                <th>总计</th>
                <th>平均输入/输出</th>
                <th>使用工具</th>
                <th>时段分布</th>
                <th>时间戳（前 10 次）</th>
                <th>示例</th>
            </tr>
            {tasks_html}
        </table>
        
        <h3 style="color: #2c3e50; background-color: #ecf0f1; padding: 8px;">🕐 24 小时调用分布</h3>
        <table border="1" cellpadding="10" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 13px;">
            <tr style="background-color: #3498db; color: white;">
                <th width="15%">时段</th>
                <th width="15%">调用次数</th>
                <th width="15%">Tokens 消耗</th>
                <th width="55%">可视化</th>
            </tr>
            {hour_html}
        </table>
        
        <h3 style="color: #2c3e50; background-color: #ecf0f1; padding: 8px;">⏰ 每次调用时间戳明细（按时间排序）</h3>
        <table border="1" cellpadding="8" cellspacing="0" style="border-collapse: collapse; width: 100%; font-size: 12px;">
            <tr style="background-color: #3498db; color: white;">
                <th width="10%">#</th>
                <th width="20%">时间</th>
                <th width="70%">任务类型</th>
            </tr>
            {timestamp_detail_html}
        </table>
        
        <h3 style="color: #2c3e50; background-color: #ecf0f1; padding: 8px;">📝 说明</h3>
        <ul style="color: #666; line-height: 2;">
            <li><strong>统计时间：</strong>{today} 00:00 - 23:59</li>
            <li><strong>使用模型：</strong>qwen3.5-plus（阿里百炼）</li>
            <li><strong>定价标准：</strong>输入 ¥0.002/千 tokens, 输出 ¥0.006/千 tokens</li>
            <li><strong>数据来源：</strong>OpenClaw 会话日志分析</li>
            <li><strong>精确统计：</strong>从明天开始，系统将自动记录每次 API 调用的精确 tokens 用量</li>
            <li><strong>报告频率：</strong>每日 20:00 自动发送</li>
            <li><strong>时间戳精度：</strong>精确到秒（HH:MM:SS）</li>
        </ul>
        
        <div style="margin-top: 30px; padding: 15px; background-color: #f8f9fa; border-left: 4px solid #3498db;">
            <p style="color: #666; font-size: 12px; margin: 0;">
                🤖 此报告由 OpenClaw 自动发送 · 百炼 API 用量监控系统 v3.0（带时间戳版）
            </p>
        </div>
    </div>
</body>
</html>
"""

# 纯文本版本
text_content = f"""
百炼 API 用量超详细日报（带时间戳） - {report['date']}
=====================================

⚠️ 注：这是首份超详细报告，tokens 为估算值。从明天开始会精确记录每次调用。

📈 核心指标:
- 总调用次数：{report['total_calls']} 次
- 输入 Tokens: {report['total_input']:,}
- 输出 Tokens: {report['total_output']:,}
- 总 Tokens 消耗：{report['total_tokens']:,}
- 平均每次调用：{avg_tokens:,} tokens
- 估算费用：¥{total_cost:.4f}
- 高峰时段：{report['peak_hour']:02d}:00（{report['peak_calls']} 次调用）
- 任务类型数：{len(detailed_tasks)} 类

📋 任务详情（按 Tokens 消耗排序）:
"""

for i, task in enumerate(detailed_tasks, 1):
    hour_dist = " ".join([f"{h}点:{c}次" for h, c in task["hour_distribution"].items()])
    timestamps_preview = ", ".join(task["timestamps"][:5])
    if len(task["timestamps"]) > 5:
        timestamps_preview += f" ... 等{len(task['timestamps'])}次"
    text_content += f"""
{i}. {task['type']}
   - 调用次数：{task['count']} 次
   - 输入：{task['input_tokens']:,} | 输出：{task['output_tokens']:,} | 总计：{task['total_tokens']:,}
   - 平均每次：输入{task['avg_input']} / 输出{task['avg_output']}
   - 使用工具：{', '.join(task['tools_used']) if task['tools_used'] else '-'}
   - 时段分布：{hour_dist}
   - 时间戳：{timestamps_preview}
   - 示例：{task['sample'][:60] if task['sample'] else '-'}
"""

text_content += f"""

🕐 24 小时调用分布:
"""
for hour in range(24):
    if hour in hour_stats:
        stats = hour_stats[hour]
        text_content += f"- {hour:02d}:00 - {stats['calls']} 次，{stats['tokens']:,} tokens\n"

text_content += f"""

⏰ 每次调用时间戳明细（按时间排序）:
"""
sorted_timestamps = sorted(report["all_timestamps"], key=lambda x: x[0])
for i, (time, task_type) in enumerate(sorted_timestamps, 1):
    text_content += f"{i:3d}. {time} - {task_type}\n"

text_content += f"""

📝 说明:
- 统计时间：{today} 00:00 - 23:59
- 使用模型：qwen3.5-plus（阿里百炼）
- 定价标准：输入 ¥0.002/千 tokens, 输出 ¥0.006/千 tokens
- 数据来源：OpenClaw 会话日志分析
- 精确统计：从明天开始，系统将自动记录每次 API 调用的精确 tokens 用量
- 报告频率：每日 20:00 自动发送
- 时间戳精度：精确到秒（HH:MM:SS）

---
🤖 此报告由 OpenClaw 自动发送 · 百炼 API 用量监控系统 v3.0（带时间戳版）
"""

try:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = EMAIL_CONFIG["from_email"]
    msg["To"] = EMAIL_CONFIG["to_email"]
    
    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))
    
    server = smtplib.SMTP_SSL(EMAIL_CONFIG["smtp_server"], EMAIL_CONFIG["smtp_port"])
    server.login(EMAIL_CONFIG["from_email"], EMAIL_CONFIG["password"])
    server.sendmail(EMAIL_CONFIG["from_email"], EMAIL_CONFIG["to_email"], msg.as_string())
    server.quit()
    
    print(f"✅ 超详细报告（带时间戳）已发送到 {EMAIL_CONFIG['to_email']}")
    print(f"   日期：{today}")
    print(f"   总调用：{report['total_calls']} 次")
    print(f"   总 tokens: {report['total_tokens']:,}")
    print(f"   平均每次：{avg_tokens:,} tokens")
    print(f"   估算费用：¥{total_cost:.4f}")
    print(f"   任务分类：{len(detailed_tasks)} 类")
    print(f"   高峰时段：{report['peak_hour']:02d}:00")
    print(f"   时间戳明细：{len(sorted_timestamps)} 条")
    
except Exception as e:
    print(f"❌ 邮件发送失败：{e}")
    import traceback
    traceback.print_exc()
