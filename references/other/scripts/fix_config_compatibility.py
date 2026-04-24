#!/usr/bin/env python3
"""
解决配置兼容性问题 - 修改健康监控的默认显示
"""
import json
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
    except Exception as e:
        return f"Error: {e}"

def main():
    print("🔧 解决配置兼容性问题...")
    
    # 方法1: 在配置文件中添加健康监控覆盖
    print("\n1. 添加健康监控配置覆盖...")
    
    # 获取当前配置
    config_cmd = "cat ~/.openclaw/openclaw.json"
    config_json = run_ssh_command(config_cmd)
    
    try:
        config = json.loads(config_json)
        
        # 添加健康监控配置
        if "health" not in config:
            config["health"] = {}
        
        config["health"]["monitor"] = {
            "agentModel": "modelstudio/qwen3.5-flash",
            "displayActualModel": True
        }
        
        # 保存修改后的配置
        new_config = json.dumps(config, indent=2, ensure_ascii=False)
        
        # 写入临时文件并传输
        with open("/tmp/openclaw_fixed.json", "w", encoding="utf-8") as f:
            f.write(new_config)
        
        transfer_cmd = "sshpass -p '123' scp -P 8022 -o StrictHostKeyChecking=no /tmp/openclaw_fixed.json u0_a46@192.168.1.9:~/.openclaw/openclaw.json"
        subprocess.run(transfer_cmd, shell=True)
        
        print("✅ 健康监控配置已添加")
        
    except Exception as e:
        print(f"❌ 配置修改失败: {e}")
        
        # 方法2: 简单地在配置中添加监控字段
        simple_fix = '''
# 在配置文件中添加以下内容来覆盖健康监控显示：
"health": {
  "monitor": {
    "agentModel": "modelstudio/qwen3.5-flash"
  }
}
'''
        print("\n💡 手动修改建议:")
        print(simple_fix)

if __name__ == "__main__":
    main()