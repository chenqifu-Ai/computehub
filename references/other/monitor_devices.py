#!/usr/bin/env python3
import subprocess
import time
import re
from datetime import datetime

# 目标MAC地址
target_mac = "50:a0:09:d9:33:d0"

print(f"🔍 开始监控网络，寻找MAC地址: {target_mac}")
print("📡 监听网络流量中... (按Ctrl+C停止)")
print("-" * 50)

# 创建arp表快照
def get_arp_table():
    try:
        # 尝试不同的arp命令
        commands = [
            ['ip', 'neigh', 'show'],
            ['arp', '-a'],
            ['arp', '-n']
        ]
        
        for cmd in commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    return result.stdout
            except:
                continue
        return ""
    except:
        return ""

def monitor_network():
    seen_devices = set()
    
    while True:
        current_time = datetime.now().strftime("%H:%M:%S")
        arp_output = get_arp_table()
        
        if arp_output:
            lines = arp_output.split('\n')
            for line in lines:
                line_lower = line.lower()
                
                # 检查是否包含目标MAC
                if target_mac.lower() in line_lower:
                    print(f"🎯 [{current_time}] 找到目标设备!")
                    print(f"   {line.strip()}")
                    
                    # 提取IP地址
                    ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', line)
                    if ip_match:
                        ip = ip_match.group()
                        print(f"   📍 IP地址: {ip}")
                        return ip
                
                # 显示新发现的设备
                ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', line)
                mac_match = re.search(r'(?:[0-9a-fA-F]{2}[:-]){5}[0-9a-fA-F]{2}', line)
                
                if ip_match and mac_match:
                    ip = ip_match.group()
                    mac = mac_match.group()
                    device_id = f"{ip}-{mac}"
                    
                    if device_id not in seen_devices:
                        seen_devices.add(device_id)
                        print(f"📱 [{current_time}] 新设备: {ip} -> {mac}")
        
        # 每5秒检查一次
        time.sleep(5)

try:
    found_ip = monitor_network()
    if found_ip:
        print(f"\n✅ 监控完成!")
        print(f"小米音箱IP地址: {found_ip}")
        print(f"MAC地址: {target_mac}")
        
        # 测试连接
        print(f"\n🧪 测试连接...")
        try:
            ping_result = subprocess.run(['ping', '-c', '2', '-W', '1', found_ip], 
                                       capture_output=True, text=True, timeout=10)
            if ping_result.returncode == 0:
                print("✅ 设备在线且可访问")
            else:
                print("⚠️  设备可能存在但无法ping通")
        except:
            print("⚠️  连接测试失败")
            
except KeyboardInterrupt:
    print("\n⏹️  监控已停止")
except Exception as e:
    print(f"\n❌ 监控出错: {e}")

print("\n💡 其他查找方法:")
print("1. 登录路由器管理界面 (192.168.1.1)")
print("2. 使用米家APP查看设备详情")
print("3. 让音箱播放音乐，观察网络流量")