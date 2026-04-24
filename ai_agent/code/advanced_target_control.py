#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对 192.168.2.134 的高级控制脚本
执行深度侦察和控制尝试
"""

import subprocess
import requests
import json
import time
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed

class AdvancedTargetController:
    def __init__(self):
        self.target = "192.168.2.134"
        self.ollama_url = f"http://{self.target}:11434"
        self.model = "gemma3:1b"
        
    def run_command(self, command, description=""):
        """执行系统命令"""
        print(f"\n[执行] {description}")
        try:
            result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
            if result.returncode == 0:
                print(f"✅ {description} 成功")
                return result.stdout
            else:
                print(f"❌ {description} 失败")
                return None
        except Exception as e:
            print(f"⚠️ {description} 异常: {e}")
            return None
    
    def quick_port_scan(self):
        """快速端口扫描 - 常用端口"""
        print("\n=== 1. 快速端口扫描 ===")
        common_ports = [21, 22, 23, 25, 53, 80, 110, 135, 139, 443, 445, 993, 995, 3389, 5985, 5986, 8080, 11434]
        open_ports = []
        
        def check_port(port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex((self.target, port))
                sock.close()
                if result == 0:
                    return port
            except:
                pass
            return None
        
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = {executor.submit(check_port, port): port for port in common_ports}
            for future in as_completed(futures):
                port = future.result()
                if port:
                    open_ports.append(port)
                    print(f"✅ 端口 {port} 开放")
        
        print(f"发现 {len(open_ports)} 个开放端口: {open_ports}")
        return open_ports
    
    def test_ollama_advanced(self):
        """Ollama 高级功能测试"""
        print("\n=== 2. Ollama 高级控制测试 ===")
        
        # 测试1: 文件系统信息（间接）
        payload1 = {
            "model": self.model,
            "prompt": "Describe the typical Windows file system structure. What are common directories?",
            "stream": False
        }
        
        try:
            response1 = requests.post(f"{self.ollama_url}/api/generate", json=payload1, timeout=30)
            if response1.status_code == 200:
                print("✅ Ollama 高级交互成功")
                # 提取关键信息
                response_text = response1.json().get('response', '')
                if 'Windows' in response_text or 'C:' in response_text:
                    print("✅ 获得有用的系统信息")
                    return True
        except Exception as e:
            print(f"❌ Ollama 高级测试失败: {e}")
        
        return False
    
    def smb_probe(self):
        """SMB 探测尝试"""
        print("\n=== 3. SMB 探测 ===")
        # 使用 smbclient 尝试连接
        result = self.run_command(f"smbclient -L //{self.target}/ -N", "SMB 共享列表探测")
        if result:
            print("✅ SMB 探测获得响应")
            return True
        else:
            print("❌ SMB 探测无响应")
            return False
    
    def http_probe(self):
        """HTTP 服务探测"""
        print("\n=== 4. HTTP 服务探测 ===")
        http_ports = [80, 8080, 8000, 3000, 5000]
        found_services = []
        
        for port in http_ports:
            try:
                url = f"http://{self.target}:{port}"
                response = requests.get(url, timeout=5)
                if response.status_code < 400:
                    found_services.append(f"{port}: {response.status_code}")
                    print(f"✅ HTTP 服务发现: 端口 {port}, 状态 {response.status_code}")
            except:
                pass
        
        return len(found_services) > 0
    
    def execute_advanced_control(self):
        """执行高级控制序列"""
        print(f"🚀 开始对 {self.target} 的高级控制")
        print("=" * 50)
        
        results = {
            "port_scan": self.quick_port_scan(),
            "ollama_advanced": self.test_ollama_advanced(),
            "smb_probe": self.smb_probe(),
            "http_probe": self.http_probe()
        }
        
        print("\n" + "=" * 50)
        print("📊 高级控制结果总结:")
        
        # 分析结果
        control_level = "基础"
        if results["ollama_advanced"]:
            control_level = "中等"
        if any([results["smb_probe"], results["http_probe"]]):
            control_level = "高级"
            
        print(f"控制级别: {control_level}")
        print(f"开放端口: {len(results['port_scan'])} 个")
        print(f"Ollama 高级控制: {'✅' if results['ollama_advanced'] else '❌'}")
        print(f"SMB 访问: {'✅' if results['smb_probe'] else '❌'}")
        print(f"HTTP 服务: {'✅' if results['http_probe'] else '❌'}")
        
        return results

if __name__ == "__main__":
    controller = AdvancedTargetController()
    results = controller.execute_advanced_control()
    
    # 保存详细结果
    import json
    from datetime import datetime
    result_file = f"/root/.openclaw/workspace/ai_agent/results/advanced_control_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(result_file, 'w') as f:
        json.dump({
            "target": "192.168.2.134",
            "timestamp": datetime.now().isoformat(),
            "results": results
        }, f, indent=2)
    
    print(f"\n💾 详细结果保存至: {result_file}")