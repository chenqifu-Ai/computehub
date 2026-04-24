#!/usr/bin/env python3
"""
Android设备Gateway启动修复脚本
解决Android不支持服务安装的问题
"""

import subprocess
import time

def run_ubuntu_command(cmd, description):
    """在Ubuntu环境中执行命令"""
    full_cmd = f"sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \"proot-distro login ubuntu -- {cmd}\""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=20)
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

def check_gateway_config():
    """检查Gateway配置"""
    print("\n📋 检查Gateway配置...")
    
    # 检查mode配置
    success, mode = run_ubuntu_command("grep -A 3 -B 3 'gateway' ~/.openclaw/openclaw.json", "Gateway配置")
    
    # 检查端口配置
    success2, port = run_ubuntu_command("grep -A 5 -B 5 'port.*18789' ~/.openclaw/openclaw.json", "端口配置")
    
    return "mode.*local" in mode if success else False, ":18789" in port if success2 else False

def stop_gateway():
    """停止Gateway"""
    run_ubuntu_command("pkill -f 'openclaw gateway' 2>/dev/null || true", "停止Gateway")
    time.sleep(2)

def start_gateway_direct():
    """直接启动Gateway（不使用服务模式）"""
    print("\n🚀 直接启动Gateway...")
    
    # Android特殊启动命令
    cmd = "openclaw gateway --no-daemon --allow-unconfigured"
    success, output = run_ubuntu_command(f"{cmd} &", "启动Gateway（直接模式）")
    
    time.sleep(3)
    return success

def check_gateway_process():
    """检查Gateway进程"""
    success, output = run_ubuntu_command("ps aux | grep 'openclaw gateway' | grep -v grep", "检查Gateway进程")
    return success, output

def check_gateway_port():
    """检查Gateway端口"""
    success, output = run_ubuntu_command("netstat -tln 2>/dev/null | grep :18789 || echo '端口检查失败'", "检查Gateway端口")
    return ":18789" in output if success else False

def main():
    """主函数"""
    print("=" * 60)
    print("📱 Android Gateway启动修复")
    print("🌐 设备: 192.168.1.9 (华为手机)")
    print("=" * 60)
    
    # 检查配置
    mode_ok, port_ok = check_gateway_config()
    print(f"\n📊 配置检查:")
    print(f"   gateway.mode: {'✅ local' if mode_ok else '❌ 需要配置'}")
    print(f"   端口18789: {'✅ 已配置' if port_ok else '❌ 未配置'}")
    
    # 停止现有进程
    stop_gateway()
    
    # 启动Gateway
    start_success = start_gateway_direct()
    
    # 检查启动结果
    process_exists, process_info = check_gateway_process()
    port_listening = check_gateway_port()
    
    print(f"\n📊 启动结果:")
    print(f"   Gateway进程: {'✅ 运行中' if process_exists else '❌ 未运行'}")
    print(f"   Gateway端口: {'✅ 监听中' if port_listening else '❌ 未监听'}")
    
    if process_exists:
        print(f"\n📝 进程信息:")
        print(process_info)
    
    if process_exists and port_listening:
        print("\n🎉 Gateway启动成功！")
        return True
    else:
        print("\n❌ Gateway启动失败")
        
        # 检查错误日志
        run_ubuntu_command("cat ~/gateway.err 2>/dev/null | tail -10", "检查错误日志")
        
        return False

if __name__ == "__main__":
    success = main()
    if success:
        print("\n✅ Android Gateway已成功启动")
    else:
        print("\n❌ 需要手动检查Android环境限制")