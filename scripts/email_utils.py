#!/usr/bin/env python3
"""
📧 统一邮件工具模块
===============
所有脚本通过此模块发送邮件，授权码只存一处。

用法:
    from email_utils import send_email, send_email_safe, test_connection
    
    # 简单发送
    send_email("主题", "正文内容")
    
    # 高级发送 (HTML + 附件)
    send_email("主题", html_body="<h1>HTML</h1>", files=["report.pdf"])
    
    # 自动重试 + 降级 (推荐)
    send_email_safe("主题", "正文")
"""

import json
import os
import ssl
import smtplib
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime
from typing import List, Optional

# ── 日志 ──
logging.basicConfig(level=logging.INFO, format="[email_utils] %(message)s")
log = logging.getLogger("email_utils")

# ── 配置路径 ──
CONFIG_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "config", "email.json")
FALLBACK_CODES = [
    "xzxveoguxylbbgbg",   # 第一次更新 (2026-04-05)
    "bzgwylbbrocdbiie",    # send-summary 用的
    "xunlwhjokescbgdd",    # 原始 (可能已过期)
]

# ── 加载配置 ──
def load_config():
    """加载邮件配置，带自动降级"""
    if os.path.exists(CONFIG_PATH):
        try:
            with open(CONFIG_PATH) as f:
                cfg = json.load(f)
            return cfg
        except Exception as e:
            log.warning(f"配置加载失败: {e}")
    
    # 环境变量降级
    env_code = os.environ.get("QQ_SMTP_PASSWORD")
    if env_code:
        log.info("使用环境变量 QQ_SMTP_PASSWORD")
        return {
            "smtp_server": "smtp.qq.com",
            "smtp_port": 587,
            "from_email": "19525456@qq.com",
            "to_email": "19525456@qq.com",
            "auth_code": env_code,
        }
    
    # 默认降级
    log.warning("⚠️ 使用内置降级授权码（请尽快更新 config/email.json）")
    return {
        "smtp_server": "smtp.qq.com",
        "smtp_port": 587,
        "from_email": "19525456@qq.com",
        "to_email": "19525456@qq.com",
        "auth_code": FALLBACK_CODES[0],
    }

# ── 连接测试 ──
def test_connection(server="smtp.qq.com", port=587, email="19525456@qq.com", code=None):
    """测试 SMTP 连接，返回 (成功, 消息)"""
    if code is None:
        cfg = load_config()
        code = cfg["auth_code"]
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        if port == 465:
            s = smtplib.SMTP_SSL(server, port, timeout=10, context=ctx)
        else:
            s = smtplib.SMTP(server, port, timeout=10)
            s.ehlo()
            s.starttls(context=ctx)
            s.ehlo()
        
        s.login(email, code)
        s.quit()
        return True, f"端口 {port} 认证成功"
    except smtplib.SMTPAuthenticationError:
        return False, f"端口 {port} 认证失败 - 授权码无效"
    except Exception as e:
        return False, f"端口 {port} 连接失败: {str(e)[:60]}"

# ── 自动修复授权码 ──
def find_working_code():
    """遍历所有已知授权码，找到有效的那个，并更新配置"""
    cfg = load_config()
    email = cfg["from_email"]
    
    for code in [cfg["auth_code"]] + FALLBACK_CODES:
        ok, msg = test_connection(email=email, code=code)
        if ok:
            # 更新配置
            cfg["auth_code"] = code
            try:
                os.makedirs(os.path.dirname(CONFIG_PATH), exist_ok=True)
                with open(CONFIG_PATH, "w") as f:
                    json.dump(cfg, f, indent=2)
                log.info(f"✅ 已自动修复授权码 -> ...{code[-4:]}")
            except Exception as e:
                log.warning(f"无法写入配置: {e}")
            return code
    
    return None

# ── 发送邮件（核心） ──
def send_email(
    subject: str,
    text_body: str = "",
    html_body: Optional[str] = None,
    to_email: Optional[str] = None,
    files: Optional[List[str]] = None,
):
    """
    发送邮件，自动尝试 SSL/STARTTLS 双端口
    
    Args:
        subject: 邮件主题
        text_body: 纯文本正文
        html_body: HTML正文（可选）
        to_email: 收件人（默认发给自己）
        files: 附件路径列表（可选）
    """
    cfg = load_config()
    server = cfg["smtp_server"]
    from_email = cfg["from_email"]
    to_email = to_email or cfg["to_email"]
    auth_code = cfg["auth_code"]
    
    # 构建邮件
    if html_body or files:
        msg = MIMEMultipart("alternative") if html_body and not files else MIMEMultipart()
    else:
        msg = MIMEMultipart("alternative")
    
    msg["From"] = from_email
    msg["To"] = to_email
    msg["Subject"] = subject
    
    if text_body:
        msg.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))
    
    if files:
        for fpath in files:
            if os.path.exists(fpath):
                with open(fpath, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header(
                        "Content-Disposition",
                        f"attachment; filename={os.path.basename(fpath)}",
                    )
                    msg.attach(part)
    
    # 发送（双端口重试）
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    last_error = None
    
    for port in [587, 465]:
        try:
            if port == 465:
                s = smtplib.SMTP_SSL(server, port, timeout=15, context=ctx)
            else:
                s = smtplib.SMTP(server, port, timeout=15)
                s.ehlo()
                s.starttls(context=ctx)
                s.ehlo()
            
            s.login(from_email, auth_code)
            s.sendmail(from_email, [to_email], msg.as_string())
            s.quit()
            log.info(f"✅ 邮件发送成功 [{subject}] 端口 {port}")
            return True
            
        except smtplib.SMTPAuthenticationError:
            last_error = "认证失败 - 授权码无效"
            log.warning(f"  ⚠️ 端口 {port}: {last_error}")
            continue
        except Exception as e:
            last_error = str(e)
            log.warning(f"  ⚠️ 端口 {port}: {last_error}")
            continue
    
    log.error(f"❌ 邮件发送失败 [{subject}]: {last_error}")
    return False

# ── 安全发送（带自动修复） ──
def send_email_safe(subject, text_body="", html_body=None, to_email=None, files=None):
    """
    发送邮件，失败时自动尝试修复授权码后重试一次
    
    这是推荐使用的函数 - 再也不会因为授权码过期而失败
    """
    result = send_email(subject, text_body, html_body, to_email, files)
    
    if not result:
        log.info("🔧 尝试自动修复授权码...")
        working = find_working_code()
        if working:
            log.info(f"✅ 已找到有效授权码，重试发送")
            result = send_email(subject, text_body, html_body, to_email, files)
            if result:
                log.info(f"✅ 重试成功")
                return True
        else:
            log.error("❌ 所有授权码均无效，请手动更新 config/email.json")
    
    return result

# ── CLI 直接调用 ──
if __name__ == "__main__":
    import sys
    
    if len(sys.argv) >= 3:
        subject = sys.argv[1]
        body = sys.argv[2]
        send_email_safe(subject, body)
    elif len(sys.argv) == 2 and sys.argv[1] == "--test":
        ok, msg = test_connection()
        print(f"{'✅' if ok else '❌'} {msg}")
    elif len(sys.argv) == 2 and sys.argv[1] == "--fix":
        code = find_working_code()
        if code:
            print(f"✅ 已找到有效授权码: ...{code[-4:]}")
        else:
            print("❌ 所有授权码均无效")
    else:
        print("用法:")
        print("  python email_utils.py --test     测试连接")
        print("  python email_utils.py --fix      自动修复授权码")
        print("  python email_utils.py '主题' '正文'  发送邮件")
