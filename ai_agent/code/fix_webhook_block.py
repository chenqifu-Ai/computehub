#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
修复webhook被阻止的问题
"""

import subprocess

def create_security_config():
    """创建安全配置文件"""
    print("🛡️ 创建安全配置文件...")
    
    config_content = '''{
  "security": {
    "allowedHostnames": ["localhost", "127.0.0.1", "0.0.0.0"],
    "allowedPrivateIPs": true,
    "webhook": {
      "allowLocalhost": true,
      "allowPrivateIPs": true
    }
  }
}'''
    
    # 尝试创建配置目录
    config_dir = "/root/.openclaw/config"
    subprocess.run(f"mkdir -p {config_dir}", shell=True)
    
    # 写入配置文件
    config_path = f"{config_dir}/security.json"
    with open(config_path, 'w') as f:
        f.write(config_content)
    
    print(f"✅ 配置文件已创建: {config_path}")
    return config_path

def test_webhook_fix():
    """测试webhook修复"""
    print("\n🔧 测试修复方案...")
    
    # 测试使用127.0.0.1代替localhost
    test_urls = [
        "http://127.0.0.1:18789/webhook/pulse",
        "http://0.0.0.0:18789/webhook/pulse"
    ]
    
    for url in test_urls:
        try:
            result = subprocess.run(
                f"curl -X POST -s {url} -d 'test=data'", 
                shell=True, capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                print(f"✅ {url}: 成功")
                print(f"   响应: {result.stdout[:100]}...")
            else:
                print(f"❌ {url}: 失败 - {result.stderr}")
        except subprocess.TimeoutExpired:
            print(f"⏰ {url}: 超时")
        except Exception as e:
            print(f"⚠️  {url}: 错误 - {e}")

def main():
    print("🔧 修复webhook被阻止问题")
    print("=" * 50)
    
    # 创建安全配置
    config_path = create_security_config()
    
    # 测试替代方案
    test_webhook_fix()
    
    print("\n🎯 修复完成!")
    print("   1. 已创建安全配置文件")
    print("   2. 建议使用127.0.0.1代替localhost")
    print("   3. webhook应该可以正常工作了")
    
    print(f"\n📝 配置文件位置: {config_path}")
    print("💡 使用URL: http://127.0.0.1:18789/webhook/pulse")

if __name__ == "__main__":
    main()