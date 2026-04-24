#!/usr/bin/env python3
"""
修复华为手机OpenClaw LAN绑定问题
"""

import subprocess
import time

def run_ssh_command(cmd, timeout=15):
    """通过SSH执行命令"""
    ssh_cmd = f"sshpass -p 123 ssh -o StrictHostKeyChecking=no -p 8022 u0_a46@192.168.2.156 '{cmd}'"
    try:
        result = subprocess.run(ssh_cmd, shell=True, capture_output=True, text=True, timeout=timeout)
        return result.returncode, result.stdout, result.stderr
    except Exception as e:
        return -1, "", str(e)

def check_current_bind_config():
    """检查当前的bind配置"""
    print("🔍 检查当前bind配置...")
    
    # 检查gateway.conf文件
    code, stdout, stderr = run_ssh_command("cat ~/.openclaw/config/gateway.conf 2>/dev/null || echo '文件不存在'")
    
    if code == 0 and "文件不存在" not in stdout:
        print("✅ 找到gateway.conf文件")
        if "127.0.0.1" in stdout or "localhost" in stdout:
            print("❌ 发现问题: bind地址配置为127.0.0.1或localhost")
            return False, stdout
        elif "0.0.0.0" in stdout:
            print("✅ bind地址已配置为0.0.0.0")
            return True, stdout
        else:
            print("⚠️  未找到明确的bind配置")
            return None, stdout
    else:
        print("❌ 无法读取gateway.conf文件")
        return False, ""

def fix_bind_config():
    """修复bind配置"""
    print("\n🔧 修复bind配置...")
    
    # 备份原配置文件
    backup_cmd = "cp ~/.openclaw/config/gateway.conf ~/.openclaw/config/gateway.conf.backup.$(date +%Y%m%d)"
    run_ssh_command(backup_cmd)
    
    # 修改bind地址为0.0.0.0
    fix_cmd = """
    if [ -f ~/.openclaw/config/gateway.conf ]; then
        # 替换127.0.0.1为0.0.0.0
        sed -i 's/127\.0\.0\.1/0.0.0.0/g' ~/.openclaw/config/gateway.conf
        sed -i 's/localhost/0.0.0.0/g' ~/.openclaw/config/gateway.conf
        
        # 确保有bind配置
        if ! grep -q "bind.*0.0.0.0" ~/.openclaw/config/gateway.conf; then
            echo 'bind: \"0.0.0.0:18789\"' >> ~/.openclaw/config/gateway.conf
        fi
        
        echo "配置已更新"
        cat ~/.openclaw/config/gateway.conf | grep -i bind
    else
        echo "创建新的gateway.conf"
        echo 'bind: "0.0.0.0:18789"' > ~/.openclaw/config/gateway.conf
        echo 'port: 18789' >> ~/.openclaw/config/gateway.conf
    fi
    """
    
    code, stdout, stderr = run_ssh_command(fix_cmd)
    if code == 0:
        print("✅ bind配置修复完成")
        print(stdout)
        return True
    else:
        print("❌ bind配置修复失败")
        print(stderr)
        return False

def restart_openclaw_service():
    """重启OpenClaw服务"""
    print("\n🔄 重启OpenClaw服务...")
    
    # 停止服务
    run_ssh_command("pkill -f openclaw")
    time.sleep(2)
    
    # 启动服务
    code, stdout, stderr = run_ssh_command("cd ~/.openclaw && nohup openclaw gateway start > gateway.log 2>&1 &")
    
    if code == 0:
        print("✅ OpenClaw服务已重启")
        time.sleep(3)  # 等待服务启动
        return True
    else:
        print("❌ OpenClaw服务重启失败")
        print(stderr)
        return False

def check_service_status():
    """检查服务状态"""
    print("\n📊 检查服务状态...")
    
    # 检查进程
    code, stdout, stderr = run_ssh_command("ps aux | grep openclaw | grep -v grep")
    if code == 0 and "openclaw" in stdout:
        print("✅ OpenClaw服务正在运行")
        print(stdout)
        return True
    else:
        print("❌ OpenClaw服务未运行")
        return False

def test_connectivity():
    """测试连接性"""
    print("\n🧪 测试连接性...")
    
    # 测试SSH连接
    code, stdout, stderr = run_ssh_command("echo 'SSH连接测试成功'")
    if code == 0:
        print("✅ SSH连接正常")
    else:
        print("❌ SSH连接失败")
    
    # 测试Gateway连接
    try:
        import requests
        response = requests.get("http://192.168.2.156:18789/status", timeout=5)
        if response.status_code == 200:
            print("✅ Gateway连接正常")
            return True
        else:
            print(f"❌ Gateway连接异常: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Gateway连接失败: {e}")
        return False

def main():
    print("🔧 华为手机OpenClaw LAN绑定问题修复")
    print("=" * 60)
    
    # 首先检查网络连接
    print("🌐 检查网络连接...")
    try:
        result = subprocess.run("ping -c 2 192.168.2.156", shell=True, capture_output=True, text=True, timeout=10)
        if result.returncode != 0:
            print("❌ 网络连接失败，请确保设备在同一网络")
            print("💡 建议: 检查WiFi连接，确认设备IP地址")
            return
    except:
        print("❌ 网络检查超时")
        return
    
    print("✅ 网络连接正常")
    
    # 检查当前配置
    config_ok, config_content = check_current_bind_config()
    
    if config_ok is False:
        # 需要修复配置
        if fix_bind_config():
            if restart_openclaw_service():
                if check_service_status():
                    test_connectivity()
    elif config_ok is True:
        print("✅ bind配置已经正确")
        test_connectivity()
    else:
        print("⚠️  配置状态未知，尝试修复...")
        if fix_bind_config():
            if restart_openclaw_service():
                check_service_status()
                test_connectivity()

if __name__ == "__main__":
    main()