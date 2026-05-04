#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Windows主机远程控制方案
目标：为Windows主机建立远程连接
"""

from pathlib import Path

def generate_windows_rdp_script():
    """生成Windows RDP连接脚本"""
    script_content = """@echo off
chcp 65001 >nul
echo 🚀 Windows RDP远程连接方案
echo ================================

echo.
echo 📋 目标主机: 192.168.2.134
echo 👤 用户名: chen  
echo 🔑 密码: c9fc9f,.
echo.

echo 🎯 连接方式:
echo 1. 使用内置远程桌面 (mstsc)
echo 2. 使用Windows PowerShell远程
echo.

echo ⚡ 推荐使用内置远程桌面:
echo.
echo 📝 手动连接步骤:
echo   1. 按 Win + R
echo   2. 输入: mstsc
echo   3. 计算机: 192.168.2.134
echo   4. 用户名: chen
echo   5. 密码: c9fc9f,.
echo.

set /p choice="请选择连接方式 (1-mstsc, 2-PowerShell): "

if "%choice%"=="1" (
    echo 🖥️ 启动远程桌面连接...
    mstsc /v:192.168.2.134
) else if "%choice%"=="2" (
    echo 💻 启动PowerShell远程...
    powershell -Command "Enter-PSSession -ComputerName 192.168.2.134 -Credential (Get-Credential)"
) else (
    echo ❌ 无效选择
    pause
    exit 1
)

echo.
echo 💡 提示: 确保目标Windows已启用远程桌面
echo.
pause
"""
    
    script_path = Path("/tmp/windows_remote.bat")
    script_path.write_text(script_content)
    return script_path

def generate_windows_setup_guide():
    """生成Windows远程设置指南"""
    guide_content = """# 🖥️ Windows主机远程设置指南

## 🎯 目标主机: 192.168.2.134 (Windows)

## 🔧 需要在目标Windows上进行的设置:

### 1. 启用远程桌面 (RDP)
```
1. 右键点击"此电脑" → 属性
2. 点击"远程桌面" 
3. 启用"远程桌面"
4. 确认防火墙允许远程桌面
```

### 2. 启用PowerShell远程 (可选)
```powershell
# 以管理员身份运行PowerShell
Enable-PSRemoting -Force
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
```

### 3. 防火墙设置
```
- 允许端口3389 (远程桌面)
- 允许端口5985 (PowerShell远程)
```

## 🚀 连接命令

### 远程桌面 (RDP)
```cmd
mstsc /v:192.168.2.134
```

### PowerShell远程
```powershell
Enter-PSSession -ComputerName 192.168.2.134 -Credential (Get-Credential)
```

### 凭据信息
- **用户名**: chen
- **密码**: c9fc9f,.

## 📋 快速检测脚本

在目标Windows上运行以下命令检查状态:

```powershell
# 检查远程桌面服务
Get-Service TermService | Select Status, StartType

# 检查防火墙规则  
Get-NetFirewallRule -DisplayName "Remote Desktop*" | Select Enabled, Profile

# 检查网络连接
test-netconnection 192.168.2.134 -Port 3389
```

## ⚠️ 注意事项

1. 确保目标主机开机并联网
2. 确保远程桌面功能已启用
3. 防火墙需要允许相关端口
4. 用户账户需要具有远程登录权限

## 🆘 故障排除

如果连接失败:
- 检查目标主机网络连接
- 确认远程桌面服务正在运行
- 检查防火墙设置
- 验证用户名和密码
"""
    
    guide_path = Path("/tmp/windows_remote_guide.md")
    guide_path.write_text(guide_content)
    return guide_path

def generate_powershell_test_script():
    """生成PowerShell测试脚本"""
    script_content = """# PowerShell远程连接测试
Write-Host "🔍 测试连接到 192.168.2.134..."

# 测试网络连通性
if (Test-NetConnection 192.168.2.134 -Port 3389).TcpTestSucceeded {
    Write-Host "✅ 网络连通性正常"
} else {
    Write-Host "❌ 网络连接失败"
    exit 1
}

# 尝试PowerShell远程
Try {
    $session = New-PSSession -ComputerName 192.168.2.134 -Credential (Get-Credential) -ErrorAction Stop
    Write-Host "✅ PowerShell远程连接成功!"
    Remove-PSSession $session
} Catch {
    Write-Host "❌ PowerShell远程失败: $($_.Exception.Message)"
    Write-Host "💡 需要在目标设备启用PowerShell远程: Enable-PSRemoting -Force"
}

Write-Host ""
Write-Host "🎯 推荐使用远程桌面:"
Write-Host "mstsc /v:192.168.2.134"
"""
    
    script_path = Path("/tmp/test_windows_remote.ps1")
    script_path.write_text(script_content)
    return script_path

def main():
    """主函数"""
    print("🖥️  Windows主机远程控制方案")
    print("=" * 50)
    print("目标主机: 192.168.2.134 (Windows)")
    print("用户名: chen")
    print("密码: c9fc9f,.")
    print("=" * 50)
    
    # 生成脚本和指南
    bat_script = generate_windows_rdp_script()
    guide = generate_windows_setup_guide()
    ps_script = generate_powershell_test_script()
    
    print("✅ 生成的文件:")
    print(f"   📜 Windows批处理脚本: {bat_script}")
    print(f"   📖 详细设置指南: {guide}")
    print(f"   🧪 PowerShell测试脚本: {ps_script}")
    
    print("\n" + "=" * 50)
    print("🚀 推荐连接方式:")
    print("1. 🖥️  远程桌面 (mstsc) - 图形界面")
    print("   mstsc /v:192.168.2.134")
    print("2. 💻 PowerShell远程 - 命令行")
    print("   Enter-PSSession -ComputerName 192.168.2.134 -Credential (Get-Credential)")
    
    print("\n" + "=" * 50)
    print("🔧 需要在目标Windows上设置:")
    print("   - 启用远程桌面")
    print("   - 配置防火墙允许RDP")
    print("   - (可选)启用PowerShell远程")
    
    print("\n" + "=" * 50)
    print("⚡ 快速启动:")
    print("   双击运行: /tmp/windows_remote.bat")

if __name__ == "__main__":
    main()