#!/usr/bin/env python3
"""
网络问题诊断脚本
功能：检查网络连接状态、DNS、网关、外网连通性
"""

import subprocess
import json
import socket
from datetime import datetime

def run_command(cmd, timeout=10):
    """执行 shell 命令并返回结果"""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, 
            text=True, timeout=timeout
        )
        return {
            'success': result.returncode == 0,
            'stdout': result.stdout.strip(),
            'stderr': result.stderr.strip(),
            'returncode': result.returncode
        }
    except subprocess.TimeoutExpired:
        return {'success': False, 'error': 'timeout'}
    except Exception as e:
        return {'success': False, 'error': str(e)}

def check_network_interface():
    """检查网络接口状态"""
    print("🔍 检查网络接口...")
    result = run_command("ip addr show | grep -E 'inet |state' | head -20")
    if result['success']:
        print(f"✅ 网络接口状态:\n{result['stdout']}")
    else:
        print(f"❌ 无法获取网络接口信息：{result.get('error', result['stderr'])}")
    return result

def check_gateway():
    """检查默认网关"""
    print("\n🔍 检查默认网关...")
    result = run_command("ip route | grep default")
    if result['success']:
        print(f"✅ 默认网关：{result['stdout']}")
    else:
        print(f"❌ 无法获取网关信息：{result.get('error', result['stderr'])}")
    return result

def check_dns():
    """检查 DNS 配置"""
    print("\n🔍 检查 DNS 配置...")
    result = run_command("cat /etc/resolv.conf | grep nameserver")
    if result['success']:
        print(f"✅ DNS 服务器:\n{result['stdout']}")
    else:
        print(f"❌ 无法获取 DNS 信息：{result.get('error', result['stderr'])}")
    return result

def ping_gateway(gateway_ip):
    """Ping 网关"""
    print(f"\n🔍 Ping 网关 {gateway_ip}...")
    result = run_command(f"ping -c 3 -W 2 {gateway_ip}")
    if result['success']:
        print(f"✅ 网关连通性正常")
    else:
        print(f"❌ 网关连通性失败")
    return result

def ping_external():
    """Ping 外网"""
    print("\n🔍 检查外网连通性...")
    targets = [
        ("8.8.8.8", "Google DNS"),
        ("114.114.114.114", "114 DNS"),
        ("baidu.com", "百度")
    ]
    
    for target, name in targets:
        result = run_command(f"ping -c 2 -W 3 {target}")
        if result['success']:
            print(f"✅ {name} ({target}): 连通")
        else:
            print(f"❌ {name} ({target}): 不通")
    return targets

def check_port_connectivity():
    """检查关键端口连通性"""
    print("\n🔍 检查关键端口...")
    ports = [
        ("192.168.1.7", 11434, "Ollama 服务器"),
        ("192.168.1.17", 18789, "OpenClaw Gateway"),
    ]
    
    for host, port, name in ports:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(3)
            result = sock.connect_ex((host, port))
            sock.close()
            if result == 0:
                print(f"✅ {name} ({host}:{port}): 开放")
            else:
                print(f"❌ {name} ({host}:{port}): 关闭/不可达")
        except Exception as e:
            print(f"❌ {name} ({host}:{port}): 错误 - {e}")

def check_routing():
    """检查路由表"""
    print("\n🔍 检查路由表...")
    result = run_command("ip route show")
    if result['success']:
        print(f"✅ 路由表:\n{result['stdout']}")
    else:
        print(f"❌ 无法获取路由表：{result.get('error', result['stderr'])}")
    return result

def main():
    print("=" * 60)
    print("🌐 网络问题诊断报告")
    print(f"⏰ 检查时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 网络接口
    check_network_interface()
    
    # 2. 网关
    gw_result = check_gateway()
    
    # 3. DNS
    check_dns()
    
    # 4. 路由
    check_routing()
    
    # 5. Ping 测试
    if gw_result['success'] and gw_result['stdout']:
        gateway_ip = gw_result['stdout'].split()[2] if len(gw_result['stdout'].split()) > 2 else None
        if gateway_ip:
            ping_gateway(gateway_ip)
    
    # 6. 外网测试
    ping_external()
    
    # 7. 端口检查
    check_port_connectivity()
    
    print("\n" + "=" * 60)
    print("✅ 网络诊断完成")
    print("=" * 60)

if __name__ == "__main__":
    main()
