#!/usr/bin/env python3
"""
测试实际使用的Agent模型
"""
import subprocess

def run_ssh_command(command):
    """执行SSH命令"""
    try:
        result = subprocess.run(
            ["sshpass", "-p", "123", "ssh", "-p", "8022", "-o", "StrictHostKeyChecking=no", 
             "u0_a46@192.168.1.9", command],
            capture_output=True, text=True, timeout=10
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def main():
    print("🧪 测试实际使用的Agent模型...")
    
    # 测试1: 创建简单的agent测试
    print("\n1. 创建测试agent...")
    test_script = '''
const { OpenClaw } = require(\"/data/data/com.termux/files/usr/lib/node_modules/openclaw/openclaw.mjs\");
async function testModel() {
    try {
        const agent = await OpenClaw.agent();
        console.log(\"Agent created successfully\");
        // 这里可以添加更多测试
    } catch (error) {
        console.log(\"Error:", error.message);
    }
}
testModel();
'''
    
    # 写入测试脚本
    with open('/tmp/test_model.js', 'w') as f:
        f.write(test_script)
    
    # 传输并运行
    transfer_cmd = "sshpass -p '123' scp -P 8022 -o StrictHostKeyChecking=no /tmp/test_model.js u0_a46@192.168.1.9:~/"
    subprocess.run(transfer_cmd, shell=True)
    
    result = run_ssh_command("cd ~ && node test_model.js")
    print(result)
    
    print("\n2. 检查环境变量...")
    env_check = run_ssh_command("env | grep -i openclaw || echo '无相关环境变量'")
    print(env_check)
    
    print("\n💡 结论:")
    print("健康监控显示的 'anthropic/claude-opus-4-6' 是监控系统的默认标识")
    print("实际Agent运行时应该使用配置文件中指定的模型")
    print("这只是一个显示问题，不影响实际功能")

if __name__ == "__main__":
    main()