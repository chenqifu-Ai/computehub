#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
远程控制脚本 - 192.168.2.134 设备
目标：建立可靠的远程连接和控制方案
"""

import os
import sys
import subprocess
import paramiko
from pathlib import Path

def check_powershell_winrm():
    """检查PowerShell WinRM远程连接"""
    print("🔍 检查PowerShell WinRM连接...")
    
    # PowerShell WinRM命令
    ps_script = """
$session = New-PSSession -ComputerName 192.168.2.134 -Credential (Get-Credential)
if ($session) {
    Write-Output "连接成功!"
    Enter-PSSession -Session $session
} else {
    Write-Output "连接失败"
}
"""
    
    print("📝 PowerShell WinRM 命令:")
    print("Enter-PSSession -ComputerName 192.168.2.134 -Credential (Get-Credential)")
    print("\n💡 需要先在目标设备启用WinRM:")
    print("Enable-PSRemoting -Force")
    return True

def check_rdp_connection():
    """检查RDP远程桌面连接"""
    print("🔍 检查RDP远程桌面连接...")
    
    # 检查本地是否有RDP客户端
    rdp_clients = [
        "xfreerdp", "rdesktop", "remmina", "mstsc.exe"
    ]
    
    available_clients = []
    for client in rdp_clients:
        try:
            subprocess.run([client, "--version"], capture_output=True, timeout=2)
            available_clients.append(client)
        except (FileNotFoundError, subprocess.TimeoutExpired):
            pass
    
    if available_clients:
        print(f"✅ 可用的RDP客户端: {', '.join(available_clients)}")
        
        if "xfreerdp" in available_clients:
            print("\n📝 xfreerdp 连接命令:")
            print("xfreerdp /v:192.168.2.134 /u:chen /p:c9fc9f,. /gfx /gdi:hw +fonts /clipboard /dynamic-resolution")
        
        if "rdesktop" in available_clients:
            print("\n📝 rdesktop 连接命令:")
            print("rdesktop -u chen -p c9fc9f,. 192.168.2.134")
        
        return True
    else:
        print("❌ 未找到RDP客户端，请安装:")
        print("Ubuntu: sudo apt install freerdp2-x11")
        print("Windows: 使用内置的mstsc")
        return False

def check_ssh_connection():
    """检查SSH连接"""
    print("🔍 检查SSH连接...")
    
    # 检查SSH客户端
    try:
        subprocess.run(["ssh", "-V"], capture_output=True, check=True)
        print("✅ SSH客户端可用")
        
        print("\n📝 SSH连接命令:")
        print("ssh chen@192.168.2.134")
        print("密码: c9fc9f,.")
        
        # 测试连接
        print("\n🧪 测试连接...")
        try:
            result = subprocess.run(
                ["ssh", "-o", "ConnectTimeout=5", "chen@192.168.2.134", "echo 'SSH测试成功'"],
                capture_output=True, timeout=10
            )
            if result.returncode == 0:
                print("✅ SSH连接成功!")
                return True
            else:
                print("❌ SSH连接失败")
                print(f"错误: {result.stderr.decode()}")
                return False
        except subprocess.TimeoutExpired:
            print("⏰ SSH连接超时，可能SSH服务未启用")
            return False
            
    except FileNotFoundError:
        print("❌ SSH客户端未安装")
        return False

def enable_ssh_on_target():
    """在目标设备启用SSH服务"""
    print("🔧 启用SSH服务方案:")
    print("\n1. 如果目标设备是Ubuntu:")
    print("   sudo apt update")
    print("   sudo apt install openssh-server")
    print("   sudo systemctl enable ssh")
    print("   sudo systemctl start ssh")
    print("   sudo ufw allow ssh")
    
    print("\n2. 如果目标设备是Windows:")
    print("   - 设置 → 应用 → 可选功能 → 添加OpenSSH服务器")
    print("   - 服务中启动SSH Server")
    print("   - 防火墙允许端口22")

def generate_control_scripts():
    """生成控制脚本"""
    scripts_dir = Path("/tmp/remote_control")
    scripts_dir.mkdir(exist_ok=True)
    
    # PowerShell脚本
    ps_script = scripts_dir / "control_192.168.2.134.ps1"
    ps_script.write_text("""
# 远程控制 192.168.2.134
Write-Host "正在连接到 192.168.2.134..."

# 方法1: PowerShell远程
Try {
    $cred = Get-Credential -Message "输入 192.168.2.134 的凭据" -UserName "chen"
    Enter-PSSession -ComputerName 192.168.2.134 -Credential $cred
} Catch {
    Write-Host "PowerShell远程失败: $($_.Exception.Message)"
    Write-Host "请确保目标设备已启用WinRM: Enable-PSRemoting -Force"
}
""")
    
    # Bash脚本
    bash_script = scripts_dir / "control_192.168.2.134.sh"
    bash_script.write_text("""
#!/bin/bash
# 远程控制 192.168.2.134

echo "正在连接到 192.168.2.134..."

# 方法1: SSH
if command -v ssh &> /dev/null; then
    echo "尝试SSH连接..."
    ssh chen@192.168.2.134
    if [ $? -eq 0 ]; then
        exit 0
    fi
fi

# 方法2: RDP (xfreerdp)
if command -v xfreerdp &> /dev/null; then
    echo "尝试RDP连接..."
    xfreerdp /v:192.168.2.134 /u:chen /p:c9fc9f,. /gfx /gdi:hw +fonts /clipboard /dynamic-resolution
    exit 0
fi

# 方法3: RDP (rdesktop)  
if command -v rdesktop &> /dev/null; then
    echo "尝试RDP连接..."
    rdesktop -u chen -p c9fc9f,. 192.168.2.134
    exit 0
fi

echo "未找到可用的远程连接工具"
echo "请安装: ssh, xfreerdp, 或 rdesktop"
""")
    
    # 设置执行权限
    bash_script.chmod(0o755)
    
    print(f"✅ 控制脚本已生成到: {scripts_dir}")
    print(f"   - PowerShell脚本: {ps_script}")
    print(f"   - Bash脚本: {bash_script}")
    
    return scripts_dir

def main():
    """主函数"""
    print("🚀 192.168.2.134 远程控制方案")
    print("=" * 50)
    
    # 检查各种连接方式
    methods = [
        ("SSH", check_ssh_connection),
        ("RDP", check_rdp_connection), 
        ("PowerShell", check_powershell_winrm)
    ]
    
    available_methods = []
    for name, check_func in methods:
        print(f"\n{'='*30}")
        print(f"{name} 连接检查")
        print(f"{'='*30}")
        if check_func():
            available_methods.append(name)
    
    print(f"\n{'='*50}")
    print("📊 可用连接方式:")
    if available_methods:
        for method in available_methods:
            print(f"✅ {method}")
    else:
        print("❌ 没有可用的远程连接方式")
        print("\n🔧 需要先配置目标设备:")
        enable_ssh_on_target()
    
    # 生成控制脚本
    print(f"\n{'='*50}")
    scripts_dir = generate_control_scripts()
    
    print(f"\n{'='*50}")
    print("🎯 推荐方案:")
    print("1. 首选SSH (最稳定安全)")
    print("2. 次选RDP (图形界面)")
    print("3. PowerShell远程 (Windows环境)")
    
    print(f"\n📁 控制脚本位置: {scripts_dir}")
    print("💡 直接运行脚本即可尝试连接")

if __name__ == "__main__":
    main()