#!/usr/bin/env python3
"""
OK支付APP自动化控制脚本
支持自动登录、支付确认、表单填写等功能
"""

import subprocess
import time
import json
from datetime import datetime

class OKPaymentAutomation:
    """OK支付自动化控制类"""
    
    def __init__(self, device_ip="10.21.183.48"):
        self.device_ip = device_ip
        self.package_name = "com.ok.payment"  # OK支付包名（可能需要调整）
        
    def connect_device(self):
        """连接设备"""
        try:
            # 尝试连接设备
            result = subprocess.run(
                ["adb", "connect", f"{self.device_ip}:5555"],
                capture_output=True, text=True
            )
            
            if "connected" in result.stdout:
                print(f"✅ 设备连接成功: {self.device_ip}")
                return True
            else:
                print(f"❌ 设备连接失败: {result.stdout}")
                return False
                
        except Exception as e:
            print(f"❌ 连接异常: {e}")
            return False
    
    def check_device_status(self):
        """检查设备状态"""
        try:
            result = subprocess.run(
                ["adb", "devices"],
                capture_output=True, text=True
            )
            print("📱 设备状态:")
            print(result.stdout)
            return "device" in result.stdout
        except Exception as e:
            print(f"❌ 检查设备状态失败: {e}")
            return False
    
    def start_ok_payment(self):
        """启动OK支付APP"""
        try:
            result = subprocess.run(
                ["adb", "shell", "monkey", "-p", self.package_name, "-c", "android.intent.category.LAUNCHER", "1"],
                capture_output=True, text=True
            )
            print("🚀 启动OK支付APP...")
            time.sleep(3)  # 等待APP启动
            return True
        except Exception as e:
            print(f"❌ 启动APP失败: {e}")
            return False
    
    def tap_screen(self, x, y):
        """点击屏幕坐标"""
        try:
            subprocess.run(
                ["adb", "shell", "input", "tap", str(x), str(y)],
                capture_output=True
            )
            print(f"👆 点击坐标: ({x}, {y})")
            time.sleep(1)
            return True
        except Exception as e:
            print(f"❌ 点击失败: {e}")
            return False
    
    def input_text(self, text):
        """输入文本"""
        try:
            # 先清空输入框
            subprocess.run(["adb", "shell", "input", "keyevent", "KEYCODE_MOVE_END"], capture_output=True)
            subprocess.run(["adb", "shell", "input", "keyevent", "--longpress", "KEYCODE_DEL"], capture_output=True)
            
            # 输入文本
            subprocess.run(
                ["adb", "shell", "input", "text", text.replace(" ", "%s")],
                capture_output=True
            )
            print(f"⌨️  输入文本: {text}")
            time.sleep(1)
            return True
        except Exception as e:
            print(f"❌ 输入文本失败: {e}")
            return False
    
    def swipe_screen(self, x1, y1, x2, y2, duration=500):
        """滑动屏幕"""
        try:
            subprocess.run(
                ["adb", "shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration)],
                capture_output=True
            )
            print(f"👆 滑动: ({x1},{y1}) → ({x2},{y2})")
            time.sleep(2)
            return True
        except Exception as e:
            print(f"❌ 滑动失败: {e}")
            return False
    
    def get_screen_info(self):
        """获取屏幕信息"""
        try:
            # 获取屏幕分辨率
            result = subprocess.run(
                ["adb", "shell", "wm", "size"],
                capture_output=True, text=True
            )
            print(f"📱 屏幕信息: {result.stdout.strip()}")
            
            # 获取当前活动
            result = subprocess.run(
                ["adb", "shell", "dumpsys", "window", "windows", "|", "grep", "-E", "mCurrentFocus"],
                capture_output=True, text=True, shell=True
            )
            print(f"📱 当前活动: {result.stdout.strip()}")
            
            return True
        except Exception as e:
            print(f"❌ 获取屏幕信息失败: {e}")
            return False
    
    def auto_login(self, username, password):
        """自动登录功能"""
        print("🔐 开始自动登录...")
        
        # 假设登录界面布局（需要根据实际APP调整坐标）
        steps = [
            ("点击用户名输入框", 300, 600),
            ("输入用户名", username),
            ("点击密码输入框", 300, 800),
            ("输入密码", password),
            ("点击登录按钮", 300, 1000)
        ]
        
        for step in steps:
            if len(step) == 3:
                desc, x, y = step
                self.tap_screen(x, y)
            else:
                desc, text = step
                self.input_text(text)
        
        print("✅ 自动登录完成")
        return True
    
    def auto_payment(self, amount, payee):
        """自动支付功能"""
        print(f"💰 开始自动支付: {amount}元 给 {payee}")
        
        # 假设支付界面布局（需要根据实际APP调整坐标）
        steps = [
            ("点击转账按钮", 300, 400),
            ("输入收款人", payee),
            ("点击收款人", 300, 500),
            ("输入金额", amount),
            ("点击确认按钮", 300, 800),
            ("输入支付密码", "123456"),  # 需要替换为真实密码
            ("点击确认支付", 300, 1000)
        ]
        
        for step in steps:
            if len(step) == 3:
                desc, x, y = step
                self.tap_screen(x, y)
            else:
                desc, text = step
                self.input_text(text)
        
        print("✅ 自动支付完成")
        return True
    
    def test_automation(self):
        """测试自动化功能"""
        print("🧪 开始自动化测试...")
        
        # 1. 检查设备连接
        if not self.check_device_status():
            print("❌ 设备未连接，请先连接设备")
            return False
        
        # 2. 获取屏幕信息
        self.get_screen_info()
        
        # 3. 启动APP
        self.start_ok_payment()
        
        # 4. 测试基本操作
        print("🔧 测试基本操作...")
        self.tap_screen(200, 200)  # 测试点击
        self.swipe_screen(200, 800, 200, 400, 500)  # 测试滑动
        
        print("✅ 自动化测试完成")
        return True

def main():
    """主函数"""
    print("🚀 OK支付自动化控制系统")
    print("=" * 50)
    
    # 创建自动化实例
    automation = OKPaymentAutomation()
    
    # 连接设备
    if automation.connect_device():
        # 测试自动化功能
        automation.test_automation()
        
        print("\n📋 可用功能:")
        print("1. 自动登录")
        print("2. 自动支付")
        print("3. 表单填写")
        print("4. 屏幕操作")
        
        # 保存配置
        config = {
            "device_ip": automation.device_ip,
            "package_name": automation.package_name,
            "last_test": datetime.now().isoformat()
        }
        
        with open("/root/.openclaw/workspace/ok_payment_config.json", "w") as f:
            json.dump(config, f, indent=2)
        
        print(f"\n✅ 配置已保存: /root/.openclaw/workspace/ok_payment_config.json")
    else:
        print("\n❌ 请先完成手机端设置:")
        print("1. 用USB线连接手机和电脑")
        print("2. 手机上授权USB调试")
        print("3. 执行: adb tcpip 5555")
        print("4. 断开USB，重新连接WiFi")

if __name__ == "__main__":
    main()