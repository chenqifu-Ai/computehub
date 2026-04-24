#!/usr/bin/env python3
"""
最终版本检查脚本
确认OpenClaw 2026.3.13版本状态
"""

import subprocess

def run_command(cmd, description):
    """执行命令并返回结果"""
    full_cmd = f"sshpass -p 123 ssh -p 8022 -o StrictHostKeyChecking=no u0_a46@192.168.1.9 \"{cmd}\""
    print(f"🔧 {description}")
    try:
        result = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            print(f"✅ 成功: {description}")
            return True, result.stdout.strip()
        else:
            print(f"❌ 失败: {description}")
            return False, result.stderr
    except Exception as e:
        print(f"💥 异常: {description} - {str(e)}")
        return False, str(e)

def check_local_version():
    """检查本机版本"""
    print("\n🦞 检查本机版本...")
    result = subprocess.run("openclaw --version", shell=True, capture_output=True, text=True)
    if result.returncode == 0:
        return result.stdout.strip()
    return "未知"

def check_termux_version():
    """检查Termux中的版本"""
    print("\n📱 检查Termux版本...")
    
    # 检查openclaw目录
    success, output = run_command("ls -la /data/data/com.termux/files/usr/lib/node_modules/ | grep openclaw", "检查OpenClaw目录")
    
    # 尝试直接运行
    success2, output2 = run_command("/data/data/com.termux/files/usr/bin/openclaw --version 2>/dev/null || echo '无法运行'", "运行OpenClaw")
    
    return output2 if success2 else "检查失败"

def check_ubuntu_config():
    """检查Ubuntu环境配置"""
    print("\n🐧 检查Ubuntu配置...")
    
    checks = [
        "ls -la ~/.openclaw/ | wc -l",
        "ls -la ~/.openclaw/workspace/ | wc -l", 
        "grep -c 'gateway' ~/.openclaw/openclaw.json",
        "cat ~/.openclaw/workspace/SOP.md | grep -c '2026.3.13' || echo '无版本信息'"
    ]
    
    results = []
    for cmd in checks:
        full_cmd = f"proot-distro login ubuntu -- {cmd}"
        success, output = run_command(full_cmd, f"Ubuntu检查: {cmd}")
        results.append(output if success else "检查失败")
    
    return results

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 OpenClaw 2026.3.13 最终版本检查")
    print("=" * 60)
    
    # 检查各环境版本
    local_version = check_local_version()
    termux_version = check_termux_version()
    ubuntu_config = check_ubuntu_config()
    
    print("\n" + "=" * 60)
    print("📊 版本检查结果")
    print("=" * 60)
    
    print(f"\n🦞 本机版本: {local_version}")
    print(f"📱 Termux版本: {termux_version}")
    
    print(f"\n🐧 Ubuntu配置状态:")
    print(f"   .openclaw目录: {ubuntu_config[0]} 项")
    print(f"   workspace目录: {ubuntu_config[1]} 项")
    print(f"   gateway配置: {ubuntu_config[2]} 处")
    print(f"   SOP版本引用: {ubuntu_config[3]}")
    
    # 版本一致性判断
    version_consistent = "2026.3.13" in local_version and "2026.3.13" in termux_version
    
    print(f"\n🎯 版本一致性: {'✅ 一致' if version_consistent else '❌ 不一致'}")
    
    if version_consistent:
        print("\n✅ 所有环境均使用 OpenClaw 2026.3.13 版本")
    else:
        print("\n⚠️ 需要检查版本一致性")

if __name__ == "__main__":
    main()