#!/usr/bin/env python3
"""
Android设备Gateway启动脚本
专门针对华为手机Android环境的Gateway启动
"""

import subprocess
import time

def run_android_command(cmd, description):
    """在Android设备上执行命令"""
    full_cmd = f"sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 '{cmd}'"
    print(f"📱 {description}")
    try:
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=30)
        if result.returncode == 0:
            print(f"✅ 成功: {description}")
            return True, result.stdout.strip()
        else:
            print(f"❌ 失败: {description}")
            print(f"错误: {result.stderr}")
            return False, result.stderr
    except Exception as e:
        print(f"💥 异常: {description} - {str(e)}")
        return False, str(e)

def check_gateway_process():
    """检查Gateway进程"""
    success, output = run_android_command("ps aux | grep 'openclaw gateway' | grep -v grep", "检查Gateway进程")
    return success, output

def check_gateway_port():
    """检查Gateway端口"""
    success, output = run_android_command("netstat -tln | grep :18789 || true", "检查Gateway端口")
    return ":18789" in output if success else False

def stop_gateway():
    """停止Gateway"""
    run_android_command("pkill -f 'openclaw gateway' || true", "停止Gateway进程")
    time.sleep(2)

def start_gateway():
    """启动Gateway"""
    # Android特殊启动方式
    cmd = "cd ~ && nohup openclaw gateway start --no-daemon > gateway.out 2> gateway.err &"
    success, _ = run_android_command(cmd, "启动Gateway服务")
    time.sleep(5)
    return success

def check_gateway_logs():
    """检查Gateway日志"""
    success, output = run_android_command("cat gateway.err 2>/dev/null | tail -5", "检查错误日志")
    success2, output2 = run_android_command("cat gateway.out 2>/dev/null | tail -5", "检查输出日志")
    return output, output2

def main():
    """主函数"""
    print("=" * 60)
    print("📱 Android Gateway启动工具")
    print("📡 目标设备: 192.168.1.9 (华为手机)")
    print("=" * 60)
    
    # 先检查当前状态
    process_exists, process_info = check_gateway_process()
    port_listening = check_gateway_port()
    
    print(f"\n📊 当前状态:")
    print(f"   Gateway进程: {'✅ 运行中' if process_exists else '❌ 未运行'}")
    print(f"   Gateway端口: {'✅ 监听中' if port_listening else '❌ 未监听'}")
    
    if process_exists and port_listening:
        print("\n🎉 Gateway已经在正常运行")
        return True
    
    # 需要启动Gateway
    print("\n🚀 开始启动Gateway...")
    
    # 先停止可能存在的进程
    stop_gateway()
    
    # 启动Gateway
    start_success = start_gateway()
    
    # 检查启动结果
    time.sleep(3)
    process_exists, process_info = check_gateway_process()
    port_listening = check_gateway_port()
    
    # 检查日志
    error_log, output_log = check_gateway_logs()
    
    print(f"\n📊 启动结果:")
    print(f"   Gateway进程: {'✅ 运行中' if process_exists else '❌ 未运行'}")
    print(f"   Gateway端口: {'✅ 监听中' if port_listening else '❌ 未监听'}")
    
    if error_log:
        print(f"\n📝 错误日志:")
        print(error_log)
    
    if output_log:
        print(f"\n📝 输出日志:")
        print(output_log)
    
    if process_exists and port_listening:
        print("\n🎉 Gateway启动成功！")
        return True
    else:
        print("\n❌ Gateway启动失败")
        
        # 尝试备用启动方式
        print("\n🔄 尝试备用启动方式...")
        run_android_command("cd ~ && openclaw gateway --help | head -10", "检查Gateway帮助")
        
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ 华为手机Gateway状态正常")
    else:
        print("\n❌ 需要手动检查Gateway配置")