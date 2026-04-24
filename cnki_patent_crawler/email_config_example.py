# 邮件配置示例
# 请复制此文件为 email_config.py 并填写真实信息

# QQ邮箱配置
QQ_EMAIL_CONFIG = {
    'sender_email': 'your_qq_number@qq.com',      # 发送邮箱
    'sender_password': 'your_authorization_code', # QQ邮箱授权码（不是密码）
    'smtp_server': 'smtp.qq.com',
    'smtp_port': 587,
}

# 接收邮箱
RECEIVER_EMAIL = '19525456@qq.com'  # 目标接收邮箱

# 如何获取QQ邮箱授权码：
# 1. 登录QQ邮箱网页版
# 2. 进入设置 → 账户
# 3. 找到"POP3/IMAP/SMTP/Exchange/CardDAV/CalDAV服务"
# 4. 开启"POP3/SMTP服务"
# 5. 根据提示发送短信，获取授权码

# 使用示例：
# from email_config import QQ_EMAIL_CONFIG, RECEIVER_EMAIL