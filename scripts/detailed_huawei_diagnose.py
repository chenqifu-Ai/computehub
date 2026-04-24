#!/usr/bin/env python3
"""
华为手机详细诊断脚本 - 精准定位LAN绑定问题
"""

import subprocess
import time

def run_ssh_command(cmd, timeout=15):
    """通过SSH执行命令"""
    ssh_cmd = f"sshpass -p 123 ssh -o StrictHostKeyChecking=no -p 8022 u0_a46@192.168.2.156 '{cmd}'"
    try:
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def check_network():
    """检查网络连通性"""
    print("🔍 检查网络连通性...")
    result = subprocess.run("ping -c 2 192.168.2.156", shell=True, capture_output=True, timeout=10)
    if result.returncode == 0:
        print("✅ 网络连通性正常")
        return True
    else:
        print("❌ 网络连通性有问题")
        return False

def check_ssh():
    """检查SSH服务"""
    print("🔍 检查SSH服务...")
    result = subprocess.run("nc -zv 192.168.2.156 8022", shell=True, capture_output=True, timeout=10)
    if result.returncode == 0:
        print("✅ SSH服务正常")
        return True
    else:
        print("❌ SSH服务异常")
        return False

def get_gateway_config():
    """获取gateway配置"""
    print("🔍 获取gateway配置...")
    code, stdout, stderr = run_ssh_command("cat ~/.openclaw/config/gateway.conf 2>/dev/null || echo 'NOT_FOUND'")
    
    if code == 0:
        if "NOT_FOUND" in stdout:
            print("❌ gateway.conf文件不存在")
            return False, ""
        else:
            print("✅ 找到gateway.conf文件")
            return True, stdout
    else:
        print("❌ 无法读取gateway.conf")
        return False, ""

def check_bind_config(config_content):
    """检查bind配置"""
    print("🔍 分析bind配置...")
    
    issues = []
    
    if "127.0.0.1" in config_content:
        issues.append("bind地址配置为127.0.0.1")
    if "localhost" in config_content:
        issues.append("bind地址配置为localhost") 
    if "0.0.0.0" not in config_content:
        issues.append("缺少0.0.0.0配置")
    
    return issues

def check_openclaw_process():
    """检查OpenClaw进程"""
    print("🔍 检查OpenClaw进程...")
    code, stdout, stderr = run_ssh_command("ps aux | grep openclaw | grep -v grep")
    
    if code == 0 and "openclaw" in stdout:
        print("✅ OpenClaw进程正在运行")
        print(f"   进程信息: {stdout.strip()}")
        return True
    else:
        print("❌ OpenClaw进程未运行")
        return False

def check_port_listening():
    """检查端口监听情况"""
    print("🔍 检查端口监听...")
    code, stdout, stderr = run_ssh_command("netstat -tlnp 2>/dev/null || ss -tlnp 2>/dev/null")
    
    if code == 0:
        if ":18789" in stdout:
            print("✅ 端口18789正在监听")
            # 检查监听地址
            if "127.0.0.1:18789" in stdout:
                print("❌ 只监听127.0.0.1 (问题所在)")
                return False
            elif "0.0.0.0:18789" in stdout:
                print("✅ 监听0.0.0.0 (正确配置)")
                return True
            else:
                print("⚠️  监听地址未知")
                return False
        else:
            print("❌ 端口18789未监听")
            return False
    else:
        print("❌ 无法检查端口状态")
        return False

def main():
    print("🔧 华为手机详细诊断")
    print("=" * 50)
    
    # 检查网络
    network_ok = check_network()
    if not network_ok:
        print("\n🚨 网络问题，无法继续诊断")
        return
    
    # 检查SSH
    ssh_ok = check_ssh()
    if not ssh_ok:
        print("\n🚨 SSH问题，无法连接设备")
        return
    
    # 获取配置
    config_exists, config_content = get_gateway_config()
    
    if config_exists:
        # 分析配置问题
        issues = check_bind_config(config_content)
        if issues:
            print(f"\n❌ 发现配置问题:")
            for issue in issues:
                print(f"   - {issue}")
        else:
            print("\n✅ 配置看起来正常")
    
    # 检查进程
    process_ok = check_openclaw_process()
    
    # 检查端口
    port_ok = check_port_listening()
    
    print("\n" + "=" * 50)
    print("📋 诊断总结:")
    
    if not network_ok:
        print("🚨 主要问题: 网络连通性")
    elif not ssh_ok:
        print("🚨 主要问题: SSH服务")
    elif not config_exists:
        print("🚨 主要问题: 配置文件缺失")
    elif issues:
        print("🚨 主要问题: bind配置错误")
    elif not process_ok:
        print("🚨 主要问题: 服务未运行") 
    elif not port_ok:
        print("🚨 主要问题: 端口监听配置")
    else:
        print("✅ 所有检查通过")
    
    print("\n💡 建议操作:")
    if issues:
        print("1. 修改gateway.conf中的bind地址")
        print("2. 重启OpenClaw服务")
    elif not process_ok:
        print("1. 启动OpenClaw服务")
    elif not port_ok:
        print("1. 检查防火墙和网络配置")

if __name__ == "__main__":
    main()