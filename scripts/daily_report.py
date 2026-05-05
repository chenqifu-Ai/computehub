#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
每日投资汇报系统 v2 - 真实数据版
每天自动获取真实股价，生成持仓报告并邮件发送
"""

from scripts.email_utils import send_email_safe
import smtplib
import json
import time
import ssl
import socket
from datetime import datetime, timedelta
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

# ─── 配置 ───
REPORT_CONFIG = {
    "email": {
        "smtp_server": "smtp.qq.com",
        "smtp_port": 587,          # STARTTLS
        "from_email": "19525456@qq.com",
        "to_email": "19525456@qq.com",
        "password": "ormxhluuafwnbgei"
    },
    "positions": {
        "600460": {"name": "士兰微", "cost": 29.364, "volume": 1000},
        "000882": {"name": "华联股份", "cost": 1.779, "volume": 22600}
    },
    "total_capital": 1000000,
    "output_dir": Path(__file__).parent.parent / "reports" / "daily",
    # 东方财富 API 字段说明
    # f43=最新价  f44=最高  f45=最低  f46=开盘  f57=代码  f58=名称  f60=昨收
    # f116=量    f117=额   f170=涨跌幅
    "api": {
        "stock_list": "https://push2.eastmoney.com/api/qt/stock/get?secid={secid}&fields=f43,f44,f45,f46,f57,f58,f60,f116,f117,f170"
    }
}


def get_stock_price(secid):
    """从东方财富 API 获取实时股价
    
    secid 格式: 1.600460 (沪市) / 0.000882 (深市)
    返回价格需除以 100
    """
    url = REPORT_CONFIG["api"]["stock_list"].format(secid=secid)
    try:
        req = Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://quote.eastmoney.com/"
        })
        resp = urlopen(req, timeout=10)
        data = json.loads(resp.read().decode("utf-8"))
        if data.get("data"):
            d = data["data"]
            prev = d.get("f60", 0) / 100
            cur = d.get("f43", 0) / 100
            if prev > 0:
                change_pct = (cur - prev) / prev * 100
            else:
                change_pct = 0
            return {
                "name": d.get("f58", ""),
                "code": d.get("f57", ""),
                "current": cur,
                "open": d.get("f46", 0) / 100,
                "high": d.get("f44", 0) / 100,
                "low": d.get("f45", 0) / 100,
                "prev_close": prev,
                "change_pct": round(change_pct, 2),
                "volume": d.get("f116", 0),
                "amount": d.get("f117", 0)
            }
    except Exception as e:
        print(f"  ⚠️ 获取 {secid} 失败: {e}")
    return None


def fetch_realtime_quotes():
    """获取所有持仓股票的实时报价"""
    stock_map = {}
    for code in REPORT_CONFIG["positions"]:
        # 上海交易所 secid=1.xxx, 深圳交易所 secid=0.xxx
        secid = f"1.{code}" if code.startswith("6") else f"0.{code}"
        print(f"  📡 获取 {code} ({secid})...")
        data = get_stock_price(secid)
        if data:
            stock_map[code] = data
            print(f"    ✅ {data['name']}: ¥{data['current']:.2f} ({data['change_pct']:+.2f}%)")
        else:
            print(f"    ❌ 获取失败，使用成本价作为代理")
    return stock_map


def generate_daily_report(stock_map):
    """基于真实数据生成每日汇报"""
    today = datetime.now().strftime("%Y-%m-%d")
    tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

    total_cost = 0
    total_value = 0
    position_details = []

    for code, pos in REPORT_CONFIG["positions"].items():
        data = stock_map.get(code, {})
        current = data.get("current", pos["cost"]) if data else pos["cost"]
        cost = pos["cost"]
        volume = pos["volume"]

        cost_amount = cost * volume
        value = current * volume
        profit = value - cost_amount
        profit_pct = (current - cost) / cost * 100

        total_cost += cost_amount
        total_value += value

        position_details.append({
            "code": code,
            "name": pos["name"],
            "cost": cost,
            "current": current,
            "volume": volume,
            "profit": profit,
            "profit_pct": round(profit_pct, 2),
            "today_change": data.get("change_pct", 0) if data else 0,
            "high": data.get("high", 0) if data else 0,
            "low": data.get("low", 0) if data else 0,
            "open": data.get("open", 0) if data else 0,
            "prev_close": data.get("prev_close", 0) if data else 0,
            "volume": data.get("volume", 0) if data else 0,
            "amount": data.get("amount", 0) if data else 0,
            "has_data": bool(data),
        })

    total_profit = total_value - total_cost
    total_profit_pct = total_profit / total_cost * 100 if total_cost else 0
    cash = REPORT_CONFIG["total_capital"] - total_cost
    position_ratio = total_value / REPORT_CONFIG["total_capital"] * 100 if REPORT_CONFIG["total_capital"] else 0

    # 生成智能次日计划
    next_day_plan = generate_next_day_plan(position_details, stock_map)

    return {
        "date": today,
        "tomorrow": tomorrow,
        "total_cost": round(total_cost, 2),
        "total_value": round(total_value, 2),
        "total_profit": round(total_profit, 2),
        "total_profit_pct": round(total_profit_pct, 2),
        "cash": round(cash, 2),
        "position_ratio": round(position_ratio, 1),
        "positions": position_details,
        "next_day_plan": next_day_plan,
        "generated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "data_source": "东方财富API"
    }


def generate_next_day_plan(positions, stock_map):
    """基于持仓数据生成智能次日计划"""
    plan = []

    for p in positions:
        code = p["code"]
        name = p["name"]
        cost = p["cost"]
        current = p["current"]
        profit_pct = p["profit_pct"]
        today_change = p["today_change"]

        # 止损位规则: 成本 -10%
        stop_loss = cost * 0.9

        if p["has_data"]:
            high = p["high"]
            low = p["low"]

        if code == "000882":
            # 华联股份 - 低价股，关注止损
            if current < stop_loss:
                plan.append(
                    f"🔴 {name}({code}): ¥{current:.2f} 跌破止损位¥{stop_loss:.2f}，累计亏损{profit_pct:+.2f}%"
                    + (f"，今日{today_change:+.2f}%，⚠️ 建议严格执行止损" if p["has_data"] else "")
                )
            elif profit_pct > 0:
                plan.append(
                    f"🟢 {name}({code}): 盈利中，关注高点做止盈"
                )
            else:
                plan.append(
                    f"⚪ {name}({code}): 接近止损位¥{stop_loss:.2f}，距成本{profit_pct:+.2f}%"
                )

        elif code == "600460":
            # 士兰微 - 半导体
            if current > cost:
                plan.append(
                    f"🟢 {name}({code}): 盈利{profit_pct:+.2f}%，可考虑在¥{cost*1.1:.2f}上方分批止盈"
                )
            elif today_change > 1:
                plan.append(
                    f"📈 {name}({code}): 今日涨{today_change:+.2}%至¥{current:.2f}，反弹中，关注能否突破¥{cost*0.98:.2f}"
                )
            else:
                plan.append(
                    f"⚪ {name}({code}): 距成本¥{cost:.3f}差距{abs(profit_pct):.2f}%，等待反弹信号"
                )

        else:
            plan.append(f"📊 {name}({code}): 距成本{profit_pct:+.2f}%，关注止损位¥{stop_loss:.2f}")

    # 仓位管理
    position_ratio = 0.0
    cash = 0
    if positions:
        position_ratio = positions[0].get("position_ratio", 0)
        cash = sum(p.get("cost_total", 0) for p in positions)
    if p and p.get("has_data", False):
        plan.append(
            f"💼 仓位{position_ratio:.1f}%，现金¥{cash:,.0f}，当前仓位偏低"
        )

    plan.append("⚠️ 严格执行止损纪律，不心存侥幸")

    return plan


def create_email_content(report):
    """创建邮件内容 (HTML + 纯文本)"""
    today = report["date"]
    tomorrow = report["tomorrow"]
    profit_color = "#28a745" if report["total_profit"] > 0 else "#dc3545"

    # ── 持仓详情行 ──
    rows_html = ""
    rows_text = ""
    for p in report["positions"]:
        clr = "#28a745" if p["profit"] > 0 else "#dc3545"
        ch_clr = "#28a745" if p["today_change"] > 0 else "#dc3545" if p["today_change"] < 0 else "#6c757d"
        status_icon = "🟢" if p["profit"] > 0 else "🔴" if p["profit"] < 0 else "⚪"

        rows_html += f"""
            <tr>
                <td style="padding:10px;border-bottom:1px solid #dee2e6;">
                    <strong>{p['name']}</strong> ({p['code']})<br>
                    <small style="color:#6c757d;">{p['volume']:,}股</small>
                </td>
                <td style="padding:10px;border-bottom:1px solid #dee2e6;text-align:right;">¥{p['cost']:.3f}</td>
                <td style="padding:10px;border-bottom:1px solid #dee2e6;text-align:right;font-weight:bold;">¥{p['current']:.2f}</td>
                <td style="padding:10px;border-bottom:1px solid #dee2e6;text-align:right;color:{ch_clr};">{p['today_change']:+.2f}%</td>
                <td style="padding:10px;border-bottom:1px solid #dee2e6;text-align:right;color:{clr};">
                    ¥{p['profit']:+,.0f} ({p['profit_pct']:+.2f}%)
                </td>
            </tr>"""

        rows_text += f"""  {status_icon} {p['name']} ({p['code']})
     成本: ¥{p['cost']:.3f} | 现价: ¥{p['current']:.2f} | 今日: {p['today_change']:+.2f}%
     盈亏: ¥{p['profit']:+,.0f} ({p['profit_pct']:+.2f}%)
"""

    # ── 次日计划 ──
    plan_html = ""
    plan_text = ""
    for i, item in enumerate(report["next_day_plan"], 1):
        plan_html += f"<li>{item}</li>\n"
        plan_text += f"  {i}. {item}\n"

    # ── HTML 邮件 ──
    html = f"""<html><body style="font-family:Microsoft YaHei,Arial,sans-serif;line-height:1.6;color:#333;">
<div style="max-width:800px;margin:0 auto;padding:20px;">

<div style="background:linear-gradient(135deg,#667eea,#764ba2);color:white;padding:20px;border-radius:10px;margin-bottom:20px;">
<h1 style="margin:0;font-size:24px;">📊 投资日报</h1>
<p style="margin:10px 0 0 0;opacity:0.9;">{today} 收盘 | 数据来源: {report['data_source']}</p>
</div>

<div style="background:#f8f9fa;padding:20px;border-radius:10px;margin-bottom:20px;">
<h2 style="margin:0 0 15px 0;color:#2d3436;">💰 资产总览</h2>
<table style="width:100%;border-collapse:collapse;">
<tr><td style="padding:10px;border-bottom:1px solid #dee2e6;"><b>总投入</b></td>
    <td style="padding:10px;border-bottom:1px solid #dee2e6;text-align:right;">¥{report['total_cost']:,.0f}</td></tr>
<tr><td style="padding:10px;border-bottom:1px solid #dee2e6;"><b>当前市值</b></td>
    <td style="padding:10px;border-bottom:1px solid #dee2e6;text-align:right;">¥{report['total_value']:,.0f}</td></tr>
<tr><td style="padding:10px;border-bottom:1px solid #dee2e6;"><b>总盈亏</b></td>
    <td style="padding:10px;border-bottom:1px solid #dee2e6;text-align:right;color:{profit_color};font-size:18px;">
        ¥{report['total_profit']:+,.0f} ({report['total_profit_pct']:+.2f}%)</td></tr>
<tr><td style="padding:10px;border-bottom:1px solid #dee2e6;"><b>现金</b></td>
    <td style="padding:10px;border-bottom:1px solid #dee2e6;text-align:right;">¥{report['cash']:,.0f}</td></tr>
<tr><td style="padding:10px;"><b>仓位</b></td>
    <td style="padding:10px;text-align:right;">{report['position_ratio']:.1f}%</td></tr>
</table></div>

<div style="background:#f8f9fa;padding:20px;border-radius:10px;margin-bottom:20px;">
<h2 style="margin:0 0 15px 0;color:#2d3436;">📈 持仓详情</h2>
<table style="width:100%;border-collapse:collapse;">
<tr style="background:#e9ecef;">
    <th style="padding:10px;text-align:left;">股票</th>
    <th style="padding:10px;text-align:right;">成本</th>
    <th style="padding:10px;text-align:right;">现价</th>
    <th style="padding:10px;text-align:right;">今日</th>
    <th style="padding:10px;text-align:right;">浮动盈亏</th>
</tr>
{rows_html}
</table></div>

<div style="background:#fff3cd;padding:20px;border-radius:10px;margin-bottom:20px;border-left:4px solid #ffc107;">
<h2 style="margin:0 0 15px 0;color:#856404;">📋 次日计划 ({tomorrow})</h2>
<ol style="margin:0;padding-left:20px;color:#856404;">
{plan_html}
</ol></div>

<div style="background:#f8d7da;padding:15px;border-radius:5px;margin-bottom:20px;">
<p style="margin:0;color:#721c24;font-size:14px;"><b>⚠️ 风险提示:</b> 投资有风险，入市需谨慎。本报告仅供参考，不构成投资建议。</p></div>

<div style="border-top:2px solid #dee2e6;padding-top:15px;color:#6c757d;font-size:12px;text-align:center;">
<p style="margin:0;">🤖 投资汇报系统自动生成 | {report['generated_at']}</p></div>
</div></body></html>"""

    # ── 纯文本邮件 ──
    text = f"""📊 投资日报 - {today}
=====================================

💰 资产总览:
  总投入: ¥{report['total_cost']:,.0f}
  当前市值: ¥{report['total_value']:,.0f}
  总盈亏: ¥{report['total_profit']:+,.0f} ({report['total_profit_pct']:+.2f}%)
  现金: ¥{report['cash']:,.0f}
  仓位: {report['position_ratio']:.1f}%

📈 持仓详情:{rows_text}
📋 次日计划 ({tomorrow}):
{plan_text}
=====================================
⚠️ 投资有风险，入市需谨慎。本报告仅供参考，不构成投资建议。
🤖 投资汇报系统 | {report['generated_at']}"""

    return f"📊 投资日报 - {today}", text, html


def send_email(subject, text_content, html_content):
    """发送邮件，支持 SMTP_SSL 和 STARTTLS 两种模式"""
    email_cfg = REPORT_CONFIG["email"]
    recipients = [email_cfg["to_email"]]

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = email_cfg["from_email"]
    msg["To"] = email_cfg["to_email"]
    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    # 尝试 STARTTLS (端口 587)
    for server, port, use_ssl in [(email_cfg["smtp_server"], 587, False),
                                  (email_cfg["smtp_server"], 465, True)]:
        try:
            print(f"  📧 尝试连接 SMTP: {server}:{port} (SSL={use_ssl})...")
            if use_ssl:
                ctx = ssl.create_default_context()
                server_obj = smtplib.SMTP_SSL(server, port, timeout=15, context=ctx)
            else:
                server_obj = smtplib.SMTP(server, port, timeout=15)
                server_obj.ehlo()
                server_obj.starttls(context=ssl.create_default_context())
                server_obj.ehlo()

            server_obj.login(email_cfg["from_email"], email_cfg["password"])
            server_obj.sendmail(email_cfg["from_email"], recipients, msg.as_string())
            server_obj.quit()
            print(f"  ✅ 邮件发送成功 → {email_cfg['to_email']}")
            return True

        except smtplib.SMTPAuthenticationError:
            print(f"  ❌ SMTP 认证失败 ({server}:{port}) - 请检查授权码")
            return False
        except ssl.SSLError as e:
            print(f"  ⚠️ SSL 错误 ({server}:{port}): {e}")
            continue
        except (ConnectionRefusedError, ConnectionResetError, socket.timeout) as e:
            print(f"  ⚠️ 连接失败 ({server}:{port}): {e}")
            continue
        except OSError as e:
            # 网络不可达，换一种方式重试
            print(f"  ⚠️ 网络错误 ({server}:{port}): {e}")
            continue
        except Exception as e:
            print(f"  ❌ SMTP 异常 ({server}:{port}): {type(e).__name__}: {e}")
            continue

    print("  ❌ 所有 SMTP 方式均失败")
    return False


def save_report(report):
    """保存报告到 JSON + Markdown"""
    output_dir = REPORT_CONFIG["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    # JSON
    json_path = output_dir / f"invest_report_{report['date']}.json"
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(f"  📁 JSON: {json_path}")

    # Markdown
    md_path = output_dir / f"invest_report_{report['date']}.md"
    lines = [
        f"# 📊 投资日报 - {report['date']}",
        f"",
        f"**数据源**: {report['data_source']}",
        f"**生成时间**: {report['generated_at']}",
        f"",
        f"## 💰 资产总览",
        f"- 总投入: ¥{report['total_cost']:,.0f}",
        f"- 当前市值: ¥{report['total_value']:,.0f}",
        f"- 总盈亏: ¥{report['total_profit']:+,.0f} ({report['total_profit_pct']:+.2f}%)",
        f"- 现金: ¥{report['cash']:,.0f}",
        f"- 仓位: {report['position_ratio']:.1f}%",
        f"",
        f"## 📈 持仓详情",
        f"",
        f"| 股票 | 成本 | 现价 | 今日 | 浮动盈亏 |",
        f"|------|------|------|------|----------|",
    ]
    for p in report["positions"]:
        ch = f"{p['today_change']:+.2f}%"
        clr = "🟢" if p["profit"] > 0 else "🔴" if p["profit"] < 0 else "⚪"
        lines.append(
            f"| {clr} {p['name']}({p['code']}) | ¥{p['cost']:.3f} | ¥{p['current']:.2f} | {ch} | "
            f"¥{p['profit']:+,.0f} ({p['profit_pct']:+.2f}%) |"
        )
    lines.append(f"\n## 📋 次日计划 ({report['tomorrow']})\n")
    for i, item in enumerate(report["next_day_plan"], 1):
        lines.append(f"{i}. {item}")
    lines.append(f"\n---")
    lines.append(f"🤖 投资汇报系统自动生成")

    with open(md_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"  📁 Markdown: {md_path}")

    return json_path, md_path


def main():
    """主函数"""
    print("=" * 70)
    print("📊 每日投资汇报系统 v2 - 真实数据版")
    print("=" * 70)

    # 1. 获取实时股价
    print("\n📡 获取实时股价...")
    stock_map = fetch_realtime_quotes()

    # 2. 生成报告
    print("\n📝 生成报告...")
    report = generate_daily_report(stock_map)

    print(f"\n  总投入: ¥{report['total_cost']:,.0f}")
    print(f"  总市值: ¥{report['total_value']:,.0f}")
    print(f"  盈亏:   ¥{report['total_profit']:+,.0f} ({report['total_profit_pct']:+.2f}%)")
    print(f"  现金:   ¥{report['cash']:,.0f} | 仓位: {report['position_ratio']:.1f}%")

    # 3. 创建邮件内容
    subject, text_content, html_content = create_email_content(report)

    # 4. 发送邮件
    print("\n📧 发送邮件...")
    send_email(subject, text_content, html_content)

    # 5. 保存报告
    print("\n💾 保存报告...")
    save_report(report)

    print("\n" + "=" * 70)
    print("✅ 日报处理完成！")
    print("=" * 70)


if __name__ == "__main__":
    main()


# TODO: 迁移到统一邮件模块
# 建议替换为:
#   from email_utils import send_email_safe
#   send_email_safe(SUBJECT, BODY)
