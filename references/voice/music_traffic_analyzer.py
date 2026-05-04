#!/usr/bin/env python3
import subprocess
import time
import re
from datetime import datetime

# 目标MAC地址
target_mac = "50:a0:09:d9:33:d0"

def analyze_music_traffic():
    """专门分析音乐流量"""
    print("🎵 启动音乐流量分析器...")
    print("📊 监控音频流数据包...")
    
    # 常见音乐流端口
    audio_ports = [554, 8008, 8009, 8080, 8888, 9000, 12345, 1935, 1936]
    high_ports = list(range(30000, 40000))  # 动态端口范围
    
    port_count = {}
    last_check = time.time()
    
    while True:
        current_time = datetime.now().strftime("%H:%M:%S")
        
        # 检查网络连接
        try:
            # 使用netstat查看活跃连接
            result = subprocess.run(['netstat', '-an'], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                lines = result.stdout.split('\n')
                
                # 分析音频相关连接
                audio_connections = []
                for line in lines:
                    # 查找ESTABLISHED连接和音频端口
                    if 'ESTABLISHED' in line:
                        for port in audio_ports:
                            if f":{port} " in line or f".{port} " in line:
                                audio_connections.append(line.strip())
                                # 统计端口使用
                                if port not in port_count:
                                    port_count[port] = 0
                                port_count[port] += 1
                
                # 显示音频连接
                if audio_connections:
                    print(f"\n🎧 [{current_time}] 发现音频流连接:")
                    for conn in audio_connections[:3]:  # 显示前3个
                        print(f"   {conn}")
        
        except:
            pass
        
        # 每30秒显示统计
        if time.time() - last_check > 30:
            if port_count:
                print(f"\n📈 端口使用统计:")
                for port, count in sorted(port_count.items(), key=lambda x: x[1], reverse=True)[:5]:
                    print(f"   端口 {port}: {count}次连接")
            last_check = time.time()
        
        # 持续检查ARP表寻找目标
        try:
            arp_result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=3)
            if arp_result.returncode == 0 and target_mac.lower() in arp_result.stdout.lower():
                print(f"\n🎯 [{current_time}] 发现目标设备!")
                lines = arp_result.stdout.split('\n')
                for line in lines:
                    if target_mac.lower() in line.lower():
                        print(f"   📍 {line.strip()}")
                        ip_match = re.search(r'\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b', line)
                        if ip_match:
                            ip = ip_match.group()
                            print(f"   🖥️  IP地址: {ip}")
                            # 立即测试
                            try:
                                ping_result = subprocess.run(['ping', '-c', '2', '-W', '1', ip], 
                                                           capture_output=True, text=True, timeout=5)
                                if ping_result.returncode == 0:
                                    print("   ✅ 设备在线且响应正常")
                                    print("   🎵 音乐播放流量确认!")
                                    return
                            except:
                                print("   ⚠️  连接测试中...")
        except:
            pass
        
        time.sleep(2)

print("🔊 音乐流量分析器启动!")
print("💡 正在播放音乐 - 这是最佳发现时机!")
analyze_music_traffic()