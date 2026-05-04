#!/usr/bin/env python3
"""
华为手机状态检查脚本
检查192.168.1.9华为手机的OpenClaw状态、服务运行情况、配置状态等
"""

import subprocess
import json
import time
from datetime import datetime

def run_command(cmd, description):
    """执行命令并返回结果"""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ 成功: {description}")
            return True, result.stdout.strip()
        else:
            print(f"❌ 失败: {description}")
            print(f"错误输出: {result.stderr}")
            return False, result.stderr
    except subprocess.TimeoutExpired:
        print(f"⏰ 超时: {description}")
        return False, "命令执行超时"
    except Exception as e:
        print(f"💥 异常: {description} - {str(e)}")
        return False, str(e)

def check_openclaw_version():
    """检查OpenClaw版本"""
    cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'openclaw --version'"
    success, output = run_command(cmd, "检查OpenClaw版本")
    if success:
        return output
    return "未知"

def check_gateway_status():
    """检查Gateway服务状态"""
    # 检查进程
    cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'ps aux | grep openclaw | grep -v grep'"
    success, output = run_command(cmd, "检查OpenClaw进程")
    
    # 检查端口
    cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'netstat -tlnp | grep :18789 || ss -tlnp | grep :18789'"
    success2, output2 = run_command(cmd, "检查Gateway端口")
    
    gateway_running = "openclaw gateway" in output if success else False
    port_listening = ":18789" in output2 if success2 else False
    
    return gateway_running, port_listening

def check_config_status():
    """检查配置状态"""
    # 检查配置文件
    cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'ls -la ~/.openclaw/workspace/config/ | wc -l'"
    success, file_count = run_command(cmd, "检查配置文件数量")
    
    # 检查关键配置文件
    config_files = ["model.conf", "email.conf", "device_identifiers.json"]
    config_status = {}
    
    for config_file in config_files:
        cmd = f"sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'cat ~/.openclaw/workspace/config/{config_file} 2>/dev/null | head -5'"
        success, content = run_command(cmd, f"检查{config_file}")
        config_status[config_file] = "存在" if success and content else "缺失"
    
    return config_status, int(file_count) - 1 if success else 0  # 减去标题行

def check_ollama_status():
    """检查Ollama状态"""
    # 检查Ollama配置
    cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'cat ~/.ollama/account.conf 2>/dev/null'"
    success, config = run_command(cmd, "检查Ollama配置")
    
    # 检查Ollama服务
    cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'curl -s http://localhost:11434/api/tags || echo \"Ollama未运行\"'"
    success2, ollama_status = run_command(cmd, "检查Ollama服务")
    
    return {
        "config_exists": success and config,
        "service_running": "models" in ollama_status if success2 else False
    }

def check_system_status():
    """检查系统状态"""
    # 内存使用
    cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'free -m | grep Mem'"
    success, memory = run_command(cmd, "检查内存使用")
    
    # 磁盘使用
    cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'df -h /data'"
    success2, disk = run_command(cmd, "检查磁盘使用")
    
    # 负载
    cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'uptime'"
    success3, uptime = run_command(cmd, "检查系统负载")
    
    return {
        "memory": memory if success else "未知",
        "disk": disk if success2 else "未知", 
        "uptime": uptime if success3 else "未知"
    }

def check_network_status():
    """检查网络状态"""
    # 检查网络连接
    cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'ping -c 2 8.8.8.8 >/dev/null 2>&1 && echo \"网络正常\" || echo \"网络异常\"'"
    success, network = run_command(cmd, "检查网络连接")
    
    # 检查公网IP
    cmd = "sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 'curl -s ifconfig.me || echo \"无法获取公网IP\"'"
    success2, public_ip = run_command(cmd, "检查公网IP")
    
    return {
        "network": network if success else "检查失败",
        "public_ip": public_ip if success2 else "未知"
    }

def generate_status_report():
    """生成状态报告"""
    print("=" * 60)
    print("📱 华为手机状态检查报告")
    print(f"🕐 检查时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📡 目标设备: 192.168.1.9 (华为手机)")
    print("=" * 60)
    
    # 检查各项状态
    version = check_openclaw_version()
    gateway_running, port_listening = check_gateway_status()
    config_status, config_count = check_config_status()
    ollama_status = check_ollama_status()
    system_status = check_system_status()
    network_status = check_network_status()
    
    print("\n" + "=" * 60)
    print("📊 状态汇总")
    print("=" * 60)
    
    # OpenClaw状态
    print(f"\n🤖 OpenClaw状态:")
    print(f"   版本: {version}")
    print(f"   Gateway进程: {'✅ 运行中' if gateway_running else '❌ 未运行'}")
    print(f"   Gateway端口: {'✅ 监听中' if port_listening else '❌ 未监听'}")
    
    # 配置状态
    print(f"\n📁 配置状态 (共{config_count}个文件):")
    for config, status in config_status.items():
        print(f"   {config}: {'✅ ' + status if status == '存在' else '❌ ' + status}")
    
    # Ollama状态
    print(f"\n🤖 Ollama状态:")
    print(f"   配置: {'✅ 存在' if ollama_status['config_exists'] else '❌ 缺失'}")
    print(f"   服务: {'✅ 运行中' if ollama_status['service_running'] else '❌ 未运行'}")
    
    # 系统状态
    print(f"\n💻 系统状态:")
    print(f"   内存: {system_status['memory']}")
    print(f"   磁盘: {system_status['disk']}")
    print(f"   运行时间: {system_status['uptime']}")
    
    # 网络状态
    print(f"\n🌐 网络状态:")
    print(f"   连接: {network_status['network']}")
    print(f"   公网IP: {network_status['public_ip']}")
    
    # 总体评估
    print(f"\n🎯 总体评估:")
    overall_status = "✅ 正常"
    if not gateway_running or not port_listening:
        overall_status = "⚠️ 警告 - Gateway服务异常"
    if not ollama_status['config_exists']:
        overall_status = "⚠️ 警告 - Ollama配置缺失"
    if "网络异常" in network_status['network']:
        overall_status = "⚠️ 警告 - 网络连接异常"
    
    print(f"   {overall_status}")
    
    return overall_status

if __name__ == "__main__":
    generate_status_report()