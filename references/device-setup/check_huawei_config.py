#!/usr/bin/env python3
"""
检查华为手机上的OpenClaw配置
"""
import subprocess
import json

def run_ssh_command(command):
    """执行SSH命令"""
    try:
        result = subprocess.run(
            ["sshpass", "-p", "123", "ssh", "-p", "8022", "-o", "StrictHostKeyChecking=no", 
             "u0_a46@192.168.1.9", command],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Timeout"
    except Exception as e:
        return f"Error: {e}"

def main():
    print("🔍 检查华为手机OpenClaw配置...")
    
    # 检查配置文件内容
    print("\n📋 配置文件内容:")
    config_cmd = "cat ~/.openclaw/openclaw.json | grep -A 10 -B 5 'primary\|default'"
    config_result = run_ssh_command(config_cmd)
    print(config_result)
    
    # 检查进程状态
    print("\n🔄 进程状态:")
    ps_cmd = "ps aux | grep openclaw | grep -v grep"
    ps_result = run_ssh_command(ps_cmd)
    print(ps_result)
    
    # 检查服务状态
    print("\n🌐 服务状态:")
    service_cmd = "curl -s http://localhost:18789/status --connect-timeout 3 >/dev/null && echo '✅ 服务正常' || echo '❌ 服务异常'"
    service_result = run_ssh_command(service_cmd)
    print(service_result)
    
    print("\n🎯 配置验证完成")

if __name__ == "__main__":
    main()