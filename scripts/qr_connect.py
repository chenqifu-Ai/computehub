#!/usr/bin/env python3
# 小智QR码扫码连接系统
# 生成包含所有访问信息的QR码

import os
import socket
import subprocess
import qrcode
from PIL import Image
import sys

def get_ip_address():
    """获取本机IP地址"""
    try:
        # 尝试连接外部服务获取公网IP
        import urllib.request
        external_ip = urllib.request.urlopen('https://api.ipify.org').read().decode('utf8')
        return external_ip
    except:
        try:
            # 获取局域网IP
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_ip = s.getsockname()[0]
            s.close()
            return local_ip
        except:
            return "未知IP"

def check_services():
    """检查服务状态"""
    services = {
        "OpenClaw Gateway": 18789,
        "SSH服务": 8022,
        "Ollama AI": 11434
    }
    
    status = {}
    for service, port in services.items():
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            status[service] = "✅ 运行中" if result == 0 else "❌ 未运行"
        except:
            status[service] = "❌ 检查失败"
    
    return status

def generate_qr_content(ip):
    """生成QR码内容"""
    content = f"""小智远程访问系统
IP地址: {ip}

访问方式:
1. Web界面: http://{ip}:18789
2. SSH连接: ssh -p 8022 root@{ip}
3. Ollama API: http://{ip}:11434

生成时间: {subprocess.getoutput('date')}
"""
    return content

def create_qr_code(content, filename="qrcode.png"):
    """创建QR码图片"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(content)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    img.save(filename)
    return filename

def display_ascii_qr(content):
    """在终端显示ASCII QR码"""
    try:
        # 使用qrencode生成ASCII QR码
        import subprocess
        result = subprocess.run(['qrencode', '-t', 'ANSI', content], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            return result.stdout
    except:
        pass
    
    # 备用方案：简单文本显示
    return "QR码内容:\n" + content

def main():
    print("🔗 小智QR码扫码连接系统")
    print("=" * 50)
    
    # 获取IP
    ip = get_ip_address()
    print(f"🌐 检测到IP地址: {ip}")
    
    # 检查服务状态
    print("\n📊 服务状态检查:")
    status = check_services()
    for service, stat in status.items():
        print(f"  {service}: {stat}")
    
    # 生成QR码内容
    qr_content = generate_qr_content(ip)
    
    print("\n📱 QR码访问信息:")
    print("-" * 30)
    print(qr_content)
    print("-" * 30)
    
    # 显示ASCII QR码
    ascii_qr = display_ascii_qr(f"http://{ip}:18789")
    print("\n📟 ASCII QR码:")
    print(ascii_qr)
    
    # 生成图片QR码
    try:
        qr_file = create_qr_code(f"http://{ip}:18789", "access_qr.png")
        print(f"\n🖼️  QR码图片已保存: {qr_file}")
        print("   用手机扫描即可访问")
    except Exception as e:
        print(f"\n⚠️  无法生成图片QR码: {e}")
    
    # 生成详细访问卡片
    print("\n💳 访问卡片:")
    print("=" * 50)
    print("设备名称: 小智AI服务器")
    print(f"IP地址: {ip}")
    print("服务端口:")
    print("  - OpenClaw Web: 18789")
    print("  - SSH服务: 8022") 
    print("  - Ollama AI: 11434")
    print("=" * 50)

if __name__ == "__main__":
    main()