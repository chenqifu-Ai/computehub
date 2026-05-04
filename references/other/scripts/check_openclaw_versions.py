#!/usr/bin/env python3
"""
OpenClaw版本检查脚本
检查华为手机上所有OpenClaw相关安装版本
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

def check_main_openclaw():
    """检查主OpenClaw版本"""
    print("\n🤖 检查主OpenClaw版本...")
    
    # 检查主版本
    success, version = run_command("openclaw --version", "OpenClaw主版本")
    
    # 检查安装位置
    success2, location = run_command("ls -la /data/data/com.termux/files/usr/bin/openclaw", "OpenClaw位置")
    
    # 检查package.json版本
    success3, pkg_version = run_command("cat /data/data/com.termux/files/usr/lib/node_modules/openclaw/package.json | grep version", "package.json版本")
    
    return version if success else "未知", location if success2 else "", pkg_version if success3 else ""

def check_wecom_version():
    """检查WeCom版本"""
    print("\n🏢 检查WeCom版本...")
    
    # 检查wecom安装
    success, wecom_files = run_command("ls -la /data/data/com.termux/files/usr/bin/ | grep wecom", "WeCom文件")
    
    # 检查wecom版本
    success2, wecom_version = run_command("cat /data/data/com.termux/files/usr/lib/node_modules/@wecom/wecom-openclaw-cli/package.json | grep version", "WeCom版本")
    
    # 尝试运行wecom
    success3, wecom_run = run_command("/data/data/com.termux/files/usr/bin/wecom-openclaw-cli --version 2>/dev/null || echo '无法运行'", "运行WeCom")
    
    return wecom_files if success else "", wecom_version if success2 else "", wecom_run if success3 else ""

def check_other_installations():
    """检查其他安装"""
    print("\n🔍 检查其他安装...")
    
    # 检查其他可能的安装位置
    locations = [
        "/data/data/com.termux/files/home/.npm/lib/node_modules",
        "/data/data/com.termux/files/home/.local/bin",
        "/data/data/com.termux/files/usr/local/bin",
        "/system/bin",
        "/system/xbin"
    ]
    
    found_installations = []
    
    for location in locations:
        success, result = run_command(f"ls -la {location} | grep -i openclaw 2>/dev/null || true", f"检查{location}")
        if success and result:
            found_installations.append(f"{location}: {result}")
    
    return found_installations

def check_npm_packages():
    """检查npm包"""
    print("\n📦 检查npm包...")
    
    # 检查全局npm包
    success, npm_list = run_command("npm list -g --depth=0 2>/dev/null | head -10", "npm全局包")
    
    # 检查已安装的openclaw相关包
    success2, openclaw_packages = run_command("npm list -g | grep -i openclaw 2>/dev/null || echo '无其他openclaw包'", "OpenClaw相关包")
    
    return npm_list if success else "", openclaw_packages if success2 else ""

def main():
    """主函数"""
    print("=" * 60)
    print("🔍 OpenClaw版本检查")
    print("📱 设备: 192.168.1.9 (华为手机)")
    print("=" * 60)
    
    # 检查各个版本
    main_version, main_location, pkg_version = check_main_openclaw()
    wecom_files, wecom_pkg, wecom_run = check_wecom_version()
    other_installations = check_other_installations()
    npm_list, openclaw_packages = check_npm_packages()
    
    print("\n" + "=" * 60)
    print("📊 版本检查结果")
    print("=" * 60)
    
    print(f"\n🤖 主OpenClaw:")
    print(f"   版本: {main_version}")
    print(f"   位置: {main_location}")
    if pkg_version:
        print(f"   package.json: {pkg_version}")
    
    print(f"\n🏢 WeCom版本:")
    if wecom_files:
        print(f"   文件: {wecom_files}")
    if wecom_pkg:
        print(f"   版本: {wecom_pkg}")
    if wecom_run:
        print(f"   运行: {wecom_run}")
    
    if other_installations:
        print(f"\n🔍 其他安装:")
        for install in other_installations:
            print(f"   {install}")
    else:
        print(f"\n🔍 其他安装: 未发现其他安装")
    
    if npm_list:
        print(f"\n📦 npm全局包:")
        print(f"   {npm_list}")
    
    if openclaw_packages:
        print(f"\n📦 OpenClaw相关包:")
        print(f"   {openclaw_packages}")
    
    print("\n✅ 版本检查完成")

if __name__ == "__main__":
    main()