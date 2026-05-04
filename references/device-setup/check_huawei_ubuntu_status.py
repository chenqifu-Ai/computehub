#!/usr/bin/env python3
"""
华为手机Ubuntu环境状态检查
检查OpenClaw、Gateway、Ollama等服务状态
"""

import subprocess

def run_ubuntu_command(cmd, description):
    """在Ubuntu环境中执行命令"""
    full_cmd = f"sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \"proot-distro login ubuntu -- {cmd}\""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ 成功: {description}")
            return True, result.stdout.strip()
        else:
            print(f"❌ 失败: {description}")
            print(f"错误: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        print(f"💥 异常: {description} - {str(e)}")
        return False, str(e)

def check_openclaw_status():
    """检查OpenClaw状态"""
    print("\n🤖 检查OpenClaw状态...")
    
    # 检查版本
    success, version = run_ubuntu_command("openclaw --version", "OpenClaw版本")
    
    # 检查安装目录
    success2, install_dir = run_ubuntu_command("which openclaw", "OpenClaw安装位置")
    
    return version if success else "未知", install_dir if success2 else "未知"

def check_gateway_status():
    """检查Gateway状态"""
    print("\n🌐 检查Gateway状态...")
    
    # 检查进程
    success, processes = run_ubuntu_command("ps aux | grep openclaw | grep -v grep", "Gateway进程")
    
    # 检查端口
    success2, ports = run_ubuntu_command("netstat -tln | grep :18789 || ss -tln | grep :18789", "Gateway端口")
    
    gateway_running = "openclaw gateway" in processes if success else False
    port_listening = ":18789" in ports if success2 else False
    
    return gateway_running, port_listening

def check_ollama_status():
    """检查Ollama状态"""
    print("\n🤖 检查Ollama状态...")
    
    # 检查服务
    success, status = run_ubuntu_command("curl -s http://localhost:11434/api/tags 2>/dev/null || echo 'Ollama未运行'", "Ollama服务")
    
    # 检查配置
    success2, config = run_ubuntu_command("cat ~/.ollama/account.conf 2>/dev/null || echo '无配置'", "Ollama配置")
    
    service_running = "models" in status if success else False
    config_exists = "api_key" in config if success2 else False
    
    return service_running, config_exists, config if success2 else ""

def check_system_status():
    """检查系统状态"""
    print("\n💻 检查系统状态...")
    
    # 内存
    success, memory = run_ubuntu_command("free -h", "内存使用")
    
    # 磁盘
    success2, disk = run_ubuntu_command("df -h /", "磁盘使用")
    
    # 负载
    success3, load = run_ubuntu_command("uptime", "系统负载")
    
    return memory if success else "", disk if success2 else "", load if success3 else ""

def check_config_status():
    """检查配置状态"""
    print("\n📁 检查配置状态...")
    
    # 检查配置目录
    success, config_files = run_ubuntu_command("ls -la ~/.openclaw/workspace/config/ | head -10", "配置文件")
    
    # 检查关键配置
    configs_to_check = ["model.conf", "email.conf", "device_identifiers.json"]
    config_status = {}
    
    for config in configs_to_check:
        success, content = run_ubuntu_command(f"cat ~/.openclaw/workspace/config/{config} 2>/dev/null | head -3", f"检查{config}")
        config_status[config] = "✅ 存在" if success and content else "❌ 缺失"
    
    return config_status

def start_gateway():
    """启动Gateway服务"""
    print("\n🚀 启动Gateway服务...")
    
    # 先停止可能存在的进程
    run_ubuntu_command("pkill -f 'openclaw gateway' || true", "停止Gateway")
    
    # 启动Gateway
    success, output = run_ubuntu_command("nohup openclaw gateway start > ~/gateway.out 2> ~/gateway.err &", "启动Gateway")
    
    # 等待一下
    import time
    time.sleep(3)
    
    # 检查启动结果
    gateway_running, port_listening = check_gateway_status()
    
    return gateway_running and port_listening

def main():
    """主函数"""
    print("=" * 60)
    print("📱 华为手机Ubuntu环境状态检查")
    print("🌐 设备: 192.168.1.9 (华为手机)")
    print("=" * 60)
    
    # 检查各项状态
    version, install_dir = check_openclaw_status()
    gateway_running, port_listening = check_gateway_status()
    ollama_running, ollama_config_exists, ollama_config = check_ollama_status()
    memory, disk, load = check_system_status()
    config_status = check_config_status()
    
    print("\n" + "=" * 60)
    print("📊 状态汇总")
    print("=" * 60)
    
    print(f"\n🤖 OpenClaw:")
    print(f"   版本: {version}")
    print(f"   位置: {install_dir}")
    
    print(f"\n🌐 Gateway:")
    print(f"   进程: {'✅ 运行中' if gateway_running else '❌ 未运行'}")
    print(f"   端口: {'✅ 监听中' if port_listening else '❌ 未监听'}")
    
    print(f"\n🤖 Ollama:")
    print(f"   服务: {'✅ 运行中' if ollama_running else '❌ 未运行'}")
    print(f"   配置: {'✅ 存在' if ollama_config_exists else '❌ 缺失'}")
    
    print(f"\n📁 配置文件:")
    for config, status in config_status.items():
        print(f"   {config}: {status}")
    
    print(f"\n💻 系统状态:")
    if memory:
        print(f"   内存: {memory.split('\\n')[1] if '\\n' in memory else memory}")
    if disk:
        print(f"   磁盘: {disk.split('\\n')[1] if '\\n' in disk else disk}")
    if load:
        print(f"   负载: {load}")
    
    # 如果Gateway未运行，尝试启动
    if not gateway_running or not port_listening:
        print(f"\n🔄 尝试启动Gateway...")
        start_success = start_gateway()
        if start_success:
            print("🎉 Gateway启动成功！")
        else:
            print("❌ Gateway启动失败")
    
    print("\n✅ 状态检查完成")

if __name__ == "__main__":
    main()