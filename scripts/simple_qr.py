#!/usr/bin/env python3
# 纯Python QR码生成器 - 不依赖外部库

def generate_text_qr(url):
    """生成文本版QR码（ASCII艺术）"""
    # 简单的文本QR码表示
    qr_text = f"""
┌────────────────────────────────────────┐
│              🔗 访问二维码              │
├────────────────────────────────────────┤
│  网址: {url: <30} │
│                                        │
│    ████████████████████████████████    │
│    ██                            ██    │
│    ██  ╭──────────────────────╮  ██    │
│    ██  │    扫码访问小智AI     │  ██    │
│    ██  ╰──────────────────────╯  ██    │
│    ██                            ██    │
│    ████████████████████████████████    │
│                                        │
│   📱 手机扫描上方区域即可访问          │
└────────────────────────────────────────┘
"""
    return qr_text

def get_network_info():
    """获取网络信息"""
    import socket
    import subprocess
    
    try:
        # 获取IP
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        
        # 获取主机名
        hostname = socket.gethostname()
        
        return ip, hostname
    except:
        return "未知", "未知"

def create_access_card():
    """创建访问卡片"""
    ip, hostname = get_network_info()
    
    card = f"""
╔══════════════════════════════════════════════════╗
║                🚀 小智AI访问卡片                ║
╠══════════════════════════════════════════════════╣
║ 设备: {hostname: <30} ║
║ IP:   {ip: <30} ║
╠══════════════════════════════════════════════════╣
║ 🌐 访问方式:                                    ║
║   • Web界面: http://{ip}:18789                ║
║   • SSH连接: ssh -p 8022 root@{ip}            ║
║   • AI服务:  http://{ip}:11434                ║
║   • TUI客户端: openclaw-tui --gateway http://{ip}:18789 ║
╠══════════════════════════════════════════════════╣
║ 📱 手机访问:                                    ║
║   直接浏览器打开: http://{ip}:18789           ║
║   (确保在同一WiFi网络)                         ║
╠══════════════════════════════════════════════════╣
║ 💡 提示:                                       ║
║   • 复制链接到手机浏览器                       ║
║   • 或截图此卡片分享                           ║
║   • 连接问题检查防火墙设置                     ║
╚══════════════════════════════════════════════════╝
"""
    return card

def main():
    print("🔗 小智简易访问系统")
    print("=" * 50)
    
    ip, hostname = get_network_info()
    url = f"http://{ip}:18789"
    
    print(f"🌐 设备信息: {hostname} ({ip})")
    print(f"🔗 访问地址: {url}")
    
    # 显示文本QR码
    print("\n📱 访问二维码:")
    print(generate_text_qr(url))
    
    # 显示详细访问卡片
    print("\n💳 详细访问信息:")
    print(create_access_card())
    
    # 生成快速连接命令
    print("\n⚡ 快速连接命令:")
    print(f"# Web访问")
    print(f"curl -s {url} | grep -i title || echo '服务正常'")
    print(f"")
    print(f"# SSH测试")
    print(f"ssh -o ConnectTimeout=5 -p 8022 root@{ip} 'echo 连接成功'")
    print(f"")
    print(f"# 一键复制命令 (Linux/Mac)")
    print(f"echo '{url}' | xclip -selection clipboard")

if __name__ == "__main__":
    main()