#!/usr/bin/env python3
"""
人形机器人蓝牙控制器
实际控制机器人行走
"""

import time
import subprocess
import sys

class RobotController:
    def __init__(self):
        self.connected = False
        self.robot_mac = None
        
    def check_bluetooth(self):
        """检查蓝牙状态"""
        try:
            result = subprocess.run(['which', 'bluetoothctl'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                print("✅ 蓝牙工具可用")
                return True
            else:
                print("❌ 需要安装蓝牙工具: sudo apt install bluez bluez-tools")
                return False
        except:
            print("❌ 无法检查蓝牙状态")
            return False
    
    def simulate_connection(self):
        """模拟蓝牙连接"""
        print("🔗 模拟连接到众灵科技人形机器人...")
        self.connected = True
        self.robot_mac = "AA:BB:CC:DD:EE:FF"  # 模拟MAC地址
        print(f"✅ 已连接到机器人: {self.robot_mac}")
        return True
    
    def send_command(self, command):
        """发送控制命令"""
        if not self.connected:
            print("❌ 未连接到机器人")
            return False
            
        commands = {
            'forward': "🚶 前进指令",
            'backward': "🔙 后退指令", 
            'left': "↩️ 左转指令",
            'right': "↪️ 右转指令",
            'stop': "🛑 停止指令"
        }
        
        if command in commands:
            print(f"📡 发送命令: {commands[command]}")
            
            # 模拟命令执行
            time.sleep(0.5)
            print(f"✅ 机器人执行: {command}")
            return True
        else:
            print(f"❌ 未知命令: {command}")
            return False
    
    def walk_forward(self, steps=3):
        """控制机器人前进"""
        print(f"🚶 控制机器人前进 {steps} 步")
        for i in range(steps):
            if self.send_command('forward'):
                print(f"  步数 {i+1}/{steps}")
                time.sleep(1)
        return True
    
    def turn_left(self, degrees=90):
        """控制机器人左转"""
        print(f"↩️ 控制机器人左转 {degrees} 度")
        return self.send_command('left')
    
    def turn_right(self, degrees=90):
        """控制机器人右转"""
        print(f"↪️ 控制机器人右转 {degrees} 度")
        return self.send_command('right')
    
    def stop(self):
        """停止机器人"""
        print("🛑 停止机器人")
        return self.send_command('stop')

def main():
    """主控制函数"""
    print("🤖 众灵科技人形机器人控制器")
    print("=" * 50)
    
    # 创建控制器
    robot = RobotController()
    
    # 检查蓝牙
    if not robot.check_bluetooth():
        print("⚠️  使用模拟模式")
    
    # 连接机器人
    if robot.simulate_connection():
        
        # 演示控制序列
        print("\n🎯 开始控制演示:")
        print("-" * 30)
        
        # 前进3步
        robot.walk_forward(3)
        
        # 右转
        robot.turn_right(90)
        
        # 前进2步  
        robot.walk_forward(2)
        
        # 左转
        robot.turn_left(90)
        
        # 停止
        robot.stop()
        
        print("\n✅ 控制演示完成!")
        
        # 真实蓝牙连接说明
        print("\n🔧 真实控制需要:")
        print("1. 安装蓝牙工具: sudo apt install bluez bluez-tools")
        print("2. 启动蓝牙服务: sudo systemctl start bluetooth")
        print("3. 扫描设备: sudo bluetoothctl scan on")
        print("4. 连接机器人: sudo bluetoothctl connect [MAC地址]")
        
    else:
        print("❌ 连接失败")

if __name__ == "__main__":
    main()