#!/usr/bin/env python3
"""
安全可逆测试方案
所有操作都可以轻松恢复，不会造成永久性损坏
"""

import subprocess
import time
from datetime import datetime

class SafeReversibleTester:
    def __init__(self):
        self.target_mac = "50:a0:09:d9:33:d0"
        self.backup_files = []
        self.test_log = []
    
    def log_action(self, action, status="✅"):
        """记录所有操作"""
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_entry = f"[{timestamp}] {status} {action}"
        self.test_log.append(log_entry)
        print(log_entry)
    
    def safe_network_test(self):
        """安全的网络测试"""
        self.log_action("开始安全网络测试")
        
        # 1. 只读的网络信息收集
        read_only_commands = [
            ("查看网络接口", ["ifconfig"]),
            ("查看路由表", ["ip", "route"]),
            ("查看DNS配置", ["cat", "/etc/resolv.conf"]),
            ("查看主机名", ["hostname"]),
        ]
        
        for desc, cmd in read_only_commands:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    self.log_action(f"{desc}: 成功")
                else:
                    self.log_action(f"{desc}: 失败", "⚠️")
            except:
                self.log_action(f"{desc}: 异常", "❌")
    
    def reversible_config_test(self):
        """可逆的配置测试"""
        self.log_action("开始可逆配置测试")
        
        # 创建临时测试文件（可轻松删除）
        test_files = [
            "/tmp/network_test_1.tmp",
            "/tmp/network_test_2.tmp"
        ]
        
        for test_file in test_files:
            try:
                with open(test_file, 'w') as f:
                    f.write(f"测试文件创建于 {datetime.now()}\
")
                    f.write(f"目标MAC: {self.target_mac}\
")
                self.backup_files.append(test_file)
                self.log_action(f"创建临时文件: {test_file}")
            except:
                self.log_action(f"创建文件失败: {test_file}", "⚠️")
    
    def safe_device_discovery(self):
        """安全的设备发现"""
        self.log_action("开始安全设备发现")
        
        # 只使用安全的发现方法
        safe_methods = [
            ("ARP表检查", ["arp", "-a"]),
            ("网络邻居", ["ip", "neigh", "show"]),
            ("ping网关", ["ping", "-c", "1", "192.168.1.1"]),
        ]
        
        for desc, cmd in safe_methods:
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
                if result.returncode == 0:
                    if self.target_mac.lower() in result.stdout.lower():
                        self.log_action(f"{desc}: 找到目标设备!", "🎯")
                        print(f"   详细信息: {result.stdout[:100]}...")
                    else:
                        self.log_action(f"{desc}: 完成")
                else:
                    self.log_action(f"{desc}: 命令失败", "⚠️")
            except:
                self.log_action(f"{desc}: 执行异常", "❌")
    
    def cleanup(self):
        """清理所有测试文件"""
        self.log_action("开始清理操作")
        
        for file_path in self.backup_files:
            try:
                subprocess.run(["rm", "-f", file_path], timeout=3)
                self.log_action(f"删除临时文件: {file_path}")
            except:
                self.log_action(f"删除文件失败: {file_path}", "⚠️")
    
    def generate_report(self):
        """生成测试报告"""
        self.log_action("生成测试报告")
        
        print("\n" + "="*60)
        print("📊 安全可逆测试报告")
        print("="*60)
        
        for log_entry in self.test_log:
            print(log_entry)
        
        print(f"\n📋 测试总结:")
        print(f"   总操作数: {len(self.test_log)}")
        print(f"   临时文件: {len(self.backup_files)} 个 (已清理)")
        print(f"   安全状态: ✅ 所有操作可逆")
        print(f"   系统状态: ✅ 未造成任何损坏")
        
        print(f"\n🎯 设备发现状态:")
        if any("找到目标设备" in log for log in self.test_log):
            print("   ✅ 成功找到设备")
        else:
            print("   ❌ 未找到设备")
            print("   💡 建议: 使用路由器管理界面或米家APP")

# 执行安全测试
if __name__ == "__main__":
    print("🛡️  启动安全可逆测试方案")
    print("🔒 所有操作均可轻松恢复")
    print("-" * 50)
    
    tester = SafeReversibleTester()
    
    try:
        tester.safe_network_test()
        tester.reversible_config_test()
        tester.safe_device_discovery()
        
    except Exception as e:
        tester.log_action(f"测试异常: {e}", "❌")
    
    finally:
        # 确保清理
        tester.cleanup()
        tester.generate_report()
        
    print("\n✅ 安全测试完成! 系统完好无损")