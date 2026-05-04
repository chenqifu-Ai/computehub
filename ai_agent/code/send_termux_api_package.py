#!/usr/bin/env python3
"""
发送 Termux:API 安装包到邮箱
"""

import smtplib
import os
import shutil
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders

def create_termux_api_package():
    """创建 Termux:API 安装包"""
    
    package_dir = "/root/.openclaw/workspace/termux_api_package"
    
    # 清理并创建目录
    if os.path.exists(package_dir):
        shutil.rmtree(package_dir)
    os.makedirs(package_dir, exist_ok=True)
    
    # 复制所有相关文件
    files_to_copy = [
        "/root/.openclaw/workspace/termux_api_install.sh",
        "/root/.openclaw/workspace/install_termux_api_simple.sh", 
        "/root/.openclaw/workspace/test_termux_api.sh",
        "/root/.openclaw/workspace/TERMUX_API_GUIDE.md"
    ]
    
    for file_path in files_to_copy:
        if os.path.exists(file_path):
            shutil.copy2(file_path, package_dir)
    
    # 创建说明文档
    readme_content = """# Termux:API 安装包

## 包含文件
- termux_api_install.sh - 完整安装脚本
- install_termux_api_simple.sh - 简化安装脚本
- test_termux_api.sh - 功能测试脚本
- TERMUX_API_GUIDE.md - 使用指南

## 安装步骤
1. 下载 Termux:API APK: https://f-droid.org/packages/com.termux.api/
2. 将本包文件复制到 Termux 的 ~/ 目录
3. 运行: bash install_termux_api_simple.sh
4. 授予必要权限

## 功能说明
- 🔦 闪光灯控制
- 📷 拍照功能
- 📍 位置服务
- 🔋 电池状态

小智 - 2026-03-25
"""
    
    with open(os.path.join(package_dir, "README.md"), "w") as f:
        f.write(readme_content)
    
    # 打包成压缩文件
    zip_path = "/root/.openclaw/workspace/termux_api_package.zip"
    shutil.make_archive(zip_path.replace('.zip', ''), 'zip', package_dir)
    
    return zip_path

def send_email_with_package():
    """发送带安装包的邮件"""
    
    # 邮件配置
    sender_email = "19525456@qq.com"
    receiver_email = "19525456@qq.com"
    password = "xunlwhjokescbgdd"
    
    # 创建安装包
    package_file = create_termux_api_package()
    
    # 邮件内容
    subject = "Termux:API 安装包"
    body = """你好！

这是你要的 Termux:API 安装包。

## 安装步骤：
1. 📱 先下载 Termux:API APK: https://f-droid.org/packages/com.termux.api/
2. 📦 解压此包到 Termux 的 ~/ 目录
3. 🔧 运行: bash install_termux_api_simple.sh
4. 🔐 授予摄像头、闪光灯等权限

## 包含功能：
- 🔦 闪光灯控制 (开/关/闪烁)
- 📷 拍照功能
- 📍 位置服务
- 🔋 电池状态
- 📞 电话功能
- 📧 短信功能

## 使用命令：
- 闪光灯: ~/flashlight_control.sh on/off/blink
- 摄像头: ~/camera_control.sh photo/info

安装完成后就可以控制手机闪光灯和摄像头了！

小智
"""
    
    # 创建邮件
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Subject'] = subject
    msg.attach(MIMEText(body, 'plain'))
    
    # 添加附件
    if os.path.exists(package_file):
        attachment = open(package_file, "rb")
        part = MIMEBase('application', 'octet-stream')
        part.set_payload(attachment.read())
        encoders.encode_base64(part)
        part.add_header('Content-Disposition', f"attachment; filename=termux_api_package.zip")
        msg.attach(part)
        attachment.close()
    
    # 发送邮件
    try:
        server = smtplib.SMTP_SSL('smtp.qq.com', 465)
        server.login(sender_email, password)
        text = msg.as_string()
        server.sendmail(sender_email, receiver_email, text)
        server.quit()
        
        print("✅ Termux:API 安装包邮件发送成功！")
        return True
        
    except Exception as e:
        print(f"❌ 邮件发送失败: {e}")
        return False

def main():
    """主函数"""
    
    print("📧 开始发送 Termux:API 安装包...")
    
    success = send_email_with_package()
    
    if success:
        print("✅ Termux:API 安装包已发送到邮箱")
        print("📬 收件人: 19525456@qq.com")
        print("📎 附件: termux_api_package.zip")
        print("")
        print("📱 安装步骤:")
        print("1. 下载 Termux:API APK")
        print("2. 解压邮件附件")
        print("3. 运行安装脚本")
    else:
        print("❌ 发送失败，请检查网络或邮箱配置")

if __name__ == "__main__":
    main()