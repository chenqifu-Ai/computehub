#!/usr/bin/env python3
"""
mail_util.py — 邮箱集中发送模块
══════════════════════════════════════════════
使用方式:
  1. 新脚本: from mail_util import send_email
  2. 改授权码: 编辑 config/email.json，不用碰任何脚本
  3. 旧脚本: 自动从 config/email.json 读取最新授权码

授权码修改说明:
  QQ邮箱 → 设置 → 账户 → POP3/SMTP服务 → 生成授权码
  然后把新授权码填到 config/email.json 的 auth_code 字段
"""

import json, os, smtplib, ssl, sys
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

_CONFIG_PATH = None  # lazy init

def _get_config_path():
    global _CONFIG_PATH
    if _CONFIG_PATH is None:
        # 从脚本位置向上找 config/email.json
        script_dir = os.path.dirname(os.path.abspath(__file__))
        workspace = os.path.dirname(script_dir)  # scripts/ 的上一级是 workspace
        _CONFIG_PATH = os.path.join(workspace, "config", "email.json")
        # 如果在 ai_agent/code/ 等深层目录，向上多级查找
        for _ in range(5):
            if os.path.exists(_CONFIG_PATH):
                break
            workspace = os.path.dirname(workspace)
            _CONFIG_PATH = os.path.join(workspace, "config", "email.json")
    return _CONFIG_PATH

def get_config():
    """读取中央邮箱配置 — 所有脚本统一从这里读"""
    config_path = _get_config_path()
    if not os.path.exists(config_path):
        raise FileNotFoundError(
            f"邮箱配置不存在: {config_path}\n"
            f"请创建 config/email.json，模板:\n"
            f'{{"smtp_server":"smtp.qq.com","smtp_port":587,"from_email":"xxx@qq.com","to_email":"xxx@qq.com","auth_code":"你的授权码"}}'
        )
    with open(config_path, "r") as f:
        return json.load(f)

def send_email(subject, text_body, html_body=None, to_addr=None, from_addr=None):
    """
    通用邮件发送函数
    
    参数:
      subject  — 邮件主题
      text_body — 纯文本内容
      html_body — HTML 内容（可选）
      to_addr   — 收件人（默认 config/email.json 的 to_email）
      from_addr — 发件人（默认 config/email.json 的 from_email）
    
    返回:
      (成功: bool, 详情: str)
    
    用法示例:
      >>> from mail_util import send_email
      >>> ok, msg = send_email("测试", "你好", "<h1>你好</h1>")
      >>> print(msg)
    """
    cfg = get_config()
    to = to_addr or cfg["to_email"]
    frm = from_addr or cfg["from_email"]
    auth = cfg["auth_code"]

    msg = MIMEMultipart("alternative")
    msg["From"] = frm
    msg["To"] = to
    msg["Subject"] = subject
    msg.attach(MIMEText(text_body, "plain", "utf-8"))
    if html_body:
        msg.attach(MIMEText(html_body, "html", "utf-8"))

    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE

    errors = []
    for port in [cfg.get("smtp_port", 587), cfg.get("smtp_port_ssl", 465)]:
        try:
            if port == 465:
                s = smtplib.SMTP_SSL(cfg["smtp_server"], port, timeout=15, context=ctx)
            else:
                s = smtplib.SMTP(cfg["smtp_server"], port, timeout=15)
                s.ehlo()
                s.starttls(context=ctx)
                s.ehlo()
            s.login(frm, auth)
            s.sendmail(frm, [to], msg.as_string())
            s.quit()
            return True, f"✅ 邮件发送成功 → {to}"
        except smtplib.SMTPAuthenticationError:
            errors.append(f"端口{port}: ❌ 认证失败 — 授权码已失效")
            errors.append("  修复: 编辑 config/email.json 的 auth_code 字段即可，无需改任何脚本")
        except smtplib.SMTPException as e:
            errors.append(f"端口{port}: SMTP错误: {str(e)[:80]}")
        except Exception as e:
            errors.append(f"端口{port}: {str(e)[:60]}")
        continue

    return False, f"❌ 发送失败\n  " + "\n  ".join(errors)


# ── 旧脚本兼容层 ──
# 以下函数是为旧脚本保持兼容，新脚本不要用

def get_auth_code():
    """旧脚本兼容：直接返回授权码"""
    return get_config()["auth_code"]

def get_email_config():
    """旧脚本兼容：返回完整配置字典"""
    return get_config()


# ── CLI 调用 ──
if __name__ == "__main__":
    subject = sys.argv[1] if len(sys.argv) > 1 else "mail_util 测试"
    text = sys.argv[2] if len(sys.argv) > 2 else "这是一封通过 mail_util.py 发送的测试邮件"
    
    try:
        ok, msg = send_email(subject, text)
        print(msg)
        sys.exit(0 if ok else 1)
    except FileNotFoundError as e:
        print(f"❌ {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ 发送异常: {e}")
        sys.exit(1)
