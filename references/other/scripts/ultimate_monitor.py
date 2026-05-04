#!/usr/bin/env python3
import subprocess
import time
import re
from datetime import datetime

# 目标MAC地址
target_mac = "50:a0:09:d9:33:d0"

def get_network_info():
    """获取所有可能的网络信息"""
    results = {}
    
    # 尝试所有ARP命令
    arp_commands = [
        ['arp', '-a'],
        ['arp', '-n'], 
        ['ip', 'neigh', 'show'],
        ['ip', 'neigh', 'list']
    ]
    
    for cmd in arp_commands:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                results[' '.join(cmd)] = result.stdout
        except:
            continue
    
    # 尝试netstat
    try:
        result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=5)
        if result.returncode == 0:
            results['netstat'] = result.stdout
    except:
        pass
    
    return results

def ultimate_monitor():
    """终极监控模式"""
    print(f"🔭 启动终极监控 - 目标: {target_mac}")
    print("📡 监控所有网络活动...")
    print("-" * 60)
    
    scan_count = 0
    last_scan_time = time.time()
    
    while True:
        current_time = datetime.now().strftime("%H:%M:%S")
        scan_count += 1
        
        # 每10秒进行一次强力扫描
        if time.time() - last_scan_time > 10:
            print(f"\n⚡ [{current_time}] 进行第{scan_count}次强力扫描...")
            # 触发一些网络活动
            subprocess.run(['ping', '-c', '1', '-b', '192.168.1.255'], 
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            last_scan_time = time.time()
        
        # 获取所有网络信息
        network_info = get_network_info()
        
        found = False
        for cmd, output in network_info.items():
            if target_mac.lower() in output.lower():
                print(f"\n🎯 [{current_time}] 在 {cmd} 中发现目标!")
                lines = output.split('\n')
                for line in lines:
                    if target_mac.lower() in line.lower():
                        print(f"   📍 {line.strip()}")
                        # 提取IP
                        ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', line)
                        if ip_match:
                            ip = ip_match.group()
                            print(f"   🖥️  IP地址: {ip}")
                            # 测试连接
                            try:
                                ping_result = subprocess.run(['ping', '-c', '1', '-W', '1', ip], 
                                                           capture_output=True, text=True, timeout=3)
                                if ping_result.returncode == 0:
                                    print("   ✅ 设备在线")
                                else:
                                    print("   ⚠️  设备无响应")
                            except:
                                print("   ❌ 连接测试失败")
                            
                            found = True
                            break
                if found:
                    break
        
        if not found:
            # 显示网络状态
            if scan_count % 5 == 0:
                total_devices = 0
                for cmd, output in network_info.items():
                    if 'arp' in cmd or 'neigh' in cmd:
                        devices = len([line for line in output.split('\n') if re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', line)])
                        total_devices += devices
                
                print(f"📊 [{current_time}] 网络状态: {total_devices}个设备在线")
        
        time.sleep(2)  # 每2秒检查一次

try:
    ultimate_monitor()
except KeyboardInterrupt:
    print("\n⏹️  监控已停止")
except Exception as e:
    print(f"\n❌ 监控错误: {e}")