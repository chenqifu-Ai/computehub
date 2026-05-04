#!/usr/bin/env python3
"""
装机技能测试脚本
验证部署功能是否正常
"""

import subprocess
import sys
import os

def test_script_exists():
    """检查部署脚本是否存在"""
    script_path = os.path.join(os.path.dirname(__file__), 'deploy.sh')
    if os.path.exists(script_path):
        print("✅ 部署脚本存在")
        return True
    else:
        print("❌ 部署脚本不存在")
        return False

def test_script_permissions():
    """检查脚本执行权限"""
    script_path = os.path.join(os.path.dirname(__file__), 'deploy.sh')
    if os.access(script_path, os.X_OK):
        print("✅ 脚本有执行权限")
        return True
    else:
        print("❌ 脚本无执行权限")
        return False

def test_sshpass_available():
    """检查sshpass是否可用"""
    try:
        result = subprocess.run(['which', 'sshpass'], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ sshpass 可用")
            return True
        else:
            print("⚠️  sshpass 不可用 (可能需要安装)")
            return False
    except Exception as e:
        print(f"❌ 检查sshpass时出错: {e}")
        return False

def test_script_syntax():
    """检查脚本语法"""
    script_path = os.path.join(os.path.dirname(__file__), 'deploy.sh')
    try:
        result = subprocess.run(['bash', '-n', script_path], 
                              capture_output=True, text=True)
        if result.returncode == 0:
            print("✅ 脚本语法正确")
            return True
        else:
            print(f"❌ 脚本语法错误: {result.stderr}")
            return False
    except Exception as e:
        print(f"❌ 检查语法时出错: {e}")
        return False

def main():
    """主测试函数"""
    print("🔧 开始装机技能测试...\n")
    
    tests = [
        test_script_exists,
        test_script_permissions, 
        test_sshpass_available,
        test_script_syntax
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        if test():
            passed += 1
        print()
    
    print(f"📊 测试结果: {passed}/{total} 通过")
    
    if passed == total:
        print("🎉 装机技能测试全部通过!")
        return 0
    else:
        print("⚠️  部分测试未通过，请检查配置")
        return 1

if __name__ == "__main__":
    sys.exit(main())