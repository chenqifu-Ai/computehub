#!/usr/bin/env python3
"""
华为手机连接测试脚本
"""

import subprocess
import sys

def test_ssh_connection():
    """测试SSH连接"""
    ip = "10.35.204.26"
    port = "8022"
    user = "u0_a46"
    password = "123"
    
    print(f"🔗 测试连接到 {user}@{ip}:{port}")
    
    # 使用sshpass测试连接
    try:
        cmd = f"sshpass -p '{password}' ssh -p {port} {user}@{ip} 'pwd'".split()
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ SSH连接成功")
            print(f"输出: {result.stdout.strip()}")
            return True
        else:
            print("❌ SSH连接失败")
            print(f"错误: {result.stderr.strip()}")
            return False
            
    except subprocess.TimeoutExpired:
        print("⏰ SSH连接超时")
        return False
    except Exception as e:
        print(f"⚠️ SSH连接异常: {e}")
        return False

def check_openclaw_status():
    """检查OpenClaw状态"""
    print("\n📊 检查OpenClaw构建状态...")
    
    # 从内存文件中读取状态
    try:
        with open('/root/.openclaw/workspace/memory/2026-04-05.md', 'r') as f:
            content = f.read()
            
        # 查找构建相关的信息
        if "OpenClaw构建" in content:
            print("✅ OpenClaw构建项目已开始")
            
            # 提取构建状态
            lines = content.split('\n')
            build_section = []
            in_build_section = False
            
            for line in lines:
                if "OpenClaw构建项目" in line:
                    in_build_section = True
                elif in_build_section and line.startswith('##') and "OpenClaw构建项目" not in line:
                    break
                elif in_build_section:
                    build_section.append(line)
            
            if build_section:
                print("📋 构建状态摘要:")
                for line in build_section[:10]:  # 显示前10行
                    if line.strip() and not line.startswith('#'):
                        print(f"   {line}")
        else:
            print("ℹ️ 未找到详细的构建记录")
            
    except FileNotFoundError:
        print("❌ 内存文件不存在")
    except Exception as e:
        print(f"⚠️ 读取内存文件错误: {e}")

def main():
    """主函数"""
    print("🤖 华为手机OpenClaw构建工作继续")
    print("=" * 50)
    
    # 测试连接
    connected = test_ssh_connection()
    
    # 检查构建状态
    check_openclaw_status()
    
    print("\n" + "=" * 50)
    
    if connected:
        print("🎯 下一步行动: 继续OpenClaw构建和依赖修复")
    else:
        print("⛔ 需要先解决连接问题")
        print("💡 建议: 检查华为手机网络状态和SSH服务")

if __name__ == "__main__":
    main()