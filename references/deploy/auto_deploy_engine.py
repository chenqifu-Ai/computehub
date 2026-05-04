#!/usr/bin/env python3
"""
OpenClaw自动部署引擎
完全自动化执行，无需人工干预
"""

import socket
import time
import subprocess
from datetime import datetime

class AutoDeployEngine:
    def __init__(self, target_host="192.168.2.134"):
        self.target_host = target_host
        self.winrm_port = 5985
        self.gateway_port = 18789
        
    def check_port(self, port, timeout=5):
        """检查端口状态"""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((self.target_host, port))
            sock.close()
            return result == 0
        except:
            return False
    
    def send_deploy_signal(self):
        """发送部署信号"""
        try:
            # 通过原始socket发送部署指令
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(10)
            sock.connect((self.target_host, self.winrm_port))
            
            # 构建简单的部署指令
            deploy_cmd = "DEPLOY_OPENCLAW::npm install -g openclaw@latest && openclaw setup && node -e \"require('openclaw').startGateway({port: 18789})\""
            
            # 发送指令
            sock.send(deploy_cmd.encode())
            sock.close()
            
            print("✅ 部署指令已发送")
            return True
            
        except Exception as e:
            print(f"❌ 指令发送失败: {e}")
            return False
    
    def monitor_deployment(self, max_checks=30, interval=10):
        """监控部署进度"""
        print(f"🔍 开始监控部署状态 (最多{max_checks}次检查)...")
        
        for check_num in range(1, max_checks + 1):
            # 检查Gateway服务
            if self.check_port(self.gateway_port, 3):
                print(f"🎉 部署成功! Gateway服务已启动 (检查 {check_num}/{max_checks})")
                print(f"🌐 访问地址: http://{self.target_host}:{self.gateway_port}")
                print(f"📊 健康检查: http://{self.target_host}:{self.gateway_port}/health")
                return True
            
            print(f"⏳ 部署进行中... (检查 {check_num}/{max_checks})")
            
            if check_num < max_checks:
                time.sleep(interval)
        
        print("❌ 部署监控超时")
        return False
    
    def execute(self):
        """执行自动部署"""
        print("=" * 60)
        print("🚀 OpenClaw自动部署引擎启动")
        print("=" * 60)
        print(f"目标设备: {self.target_host}")
        print(f"开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("-" * 60)
        
        # 1. 检查WinRM服务
        print("1. 检查WinRM服务状态...")
        if self.check_port(self.winrm_port):
            print("   ✅ WinRM服务正常运行")
        else:
            print("   ❌ WinRM服务不可用")
            return False
        
        # 2. 发送部署指令
        print("\\n2. 发送部署指令...")
        if self.send_deploy_signal():
            print("   ✅ 部署指令发送成功")
        else:
            print("   ⚠️  指令发送受限，使用监控模式")
        
        # 3. 监控部署状态
        print("\\n3. 监控部署进度...")
        success = self.monitor_deployment()
        
        print("\\n" + "=" * 60)
        if success:
            print("✅ 自动部署完成!")
            print("📍 OpenClaw服务正常运行")
        else:
            print("❌ 自动部署失败")
            print("💡 需要手动执行部署命令")
        
        return success

# 执行自动部署
if __name__ == "__main__":
    engine = AutoDeployEngine("192.168.2.134")
    engine.execute()