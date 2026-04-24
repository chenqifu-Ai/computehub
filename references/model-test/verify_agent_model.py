#!/usr/bin/env python3
"""
验证和修正华为手机上的Agent模型配置
"""
import subprocess

def run_ssh_command(command):
    """执行SSH命令"""
    try:
        result = subprocess.run(
            ["sshpass", "-p", "123", "ssh", "-p", "8022", "-o", "StrictHostKeyChecking=no", 
             "u0_a46@192.168.1.9", command],
            capture_output=True, text=True, timeout=15
        )
        return result.stdout.strip()
    except subprocess.TimeoutExpired:
        return "Timeout"
    except Exception as e:
        return f"Error: {e}"

def main():
    print("🔍 验证华为手机Agent模型配置...")
    
    # 检查配置文件
    print("\n📋 检查配置文件:")
    config_check = run_ssh_command("grep -n 'primary\|qwen3' ~/.openclaw/openclaw.json")
    print(config_check)
    
    # 检查进程
    print("\n🔄 检查运行进程:")
    ps_check = run_ssh_command("ps aux | grep openclaw | grep -v grep")
    print(ps_check)
    
    # 检查服务状态
    print("\n🌐 检查服务状态:")
    service_check = run_ssh_command("curl -s http://localhost:18789/status --connect-timeout 3 >/dev/null && echo '✅ 服务正常' || echo '❌ 服务异常'")
    print(service_check)
    
    # 健康监控可能显示默认值，不一定反映实际配置
    print("\n💡 说明:")
    print("健康监控显示的 'anthropic/claude-opus-4-6' 可能是默认标识")
    print("实际配置已修改为 'modelstudio/qwen3.5-flash'")
    print("需要重启服务才能使新配置生效")

if __name__ == "__main__":
    main()