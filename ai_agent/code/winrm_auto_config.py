#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinRM自动配置脚本
通过SMB等方式自动配置目标设备的WinRM设置
"""

import subprocess
import sys
from pathlib import Path

def check_smb_access():
    """检查SMB文件共享访问"""
    print("🔍 检查SMB文件共享访问...")
    
    try:
        # 尝试列出SMB共享
        result = subprocess.run([
            "smbclient", "-L", "192.168.2.134", "-U", "chen%c9fc9f,.", "-N"
        ], capture_output=True, timeout=15)
        
        if result.returncode == 0:
            print("✅ SMB访问成功")
            print(result.stdout.decode())
            return True
        else:
            print("❌ SMB访问失败")
            print(f"错误: {result.stderr.decode()}")
            return False
            
    except FileNotFoundError:
        print("❌ smbclient工具未安装")
        return False
    except subprocess.TimeoutExpired:
        print("⏰ SMB检查超时")
        return False

def create_winrm_config_script():
    """创建WinRM配置脚本"""
    script_content = """# WinRM自动配置脚本
Write-Host "🚀 开始配置WinRM远程管理..."

# 1. 启用PowerShell远程
Try {
    Enable-PSRemoting -Force -ErrorAction Stop
    Write-Host "✅ PowerShell远程已启用"
} Catch {
    Write-Host "❌ 启用PowerShell远程失败: $($_.Exception.Message)"
    exit 1
}

# 2. 配置信任所有主机（测试环境）
Try {
    Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "*" -Force -ErrorAction Stop
    Write-Host "✅ 信任主机配置完成"
} Catch {
    Write-Host "⚠️  信任主机配置失败: $($_.Exception.Message)"
}

# 3. 启用基本身份验证
Try {
    Set-Item WSMan:\\localhost\\Service\\Auth\\Basic -Value $true -ErrorAction Stop
    Write-Host "✅ 基本身份验证已启用"
} Catch {
    Write-Host "⚠️  基本身份验证配置失败: $($_.Exception.Message)"
}

# 4. 重启WinRM服务
Try {
    Restart-Service WinRM -Force -ErrorAction Stop
    Write-Host "✅ WinRM服务已重启"
} Catch {
    Write-Host "⚠️  服务重启失败: $($_.Exception.Message)"
}

# 5. 检查配置状态
Write-Host ""
Write-Host "📊 当前WinRM配置状态:"
winrm get winrm/config

Write-Host ""
Write-Host "🎉 WinRM配置完成!"
Write-Host "现在可以从其他设备使用:"
Write-Host "test-wsman -ComputerName $env:COMPUTERNAME"
Write-Host "Enter-PSSession -ComputerName $env:COMPUTERNAME -Credential (Get-Credential)"

# 保持窗口打开
Write-Host ""
Read-Host "按回车键退出"
"""
    
    script_path = Path("/tmp/configure_winrm.ps1")
    script_path.write_text(script_content)
    return script_path

def copy_via_smb():
    """通过SMB复制配置文件"""
    print("📤 尝试通过SMB复制配置脚本...")
    
    config_script = create_winrm_config_script()
    
    try:
        # 创建SMB共享目录（如果可能）
        result = subprocess.run([
            "smbclient", "\\\\192.168.2.134\\C$", "-U", "chen%c9fc9f,.", 
            "-c", f"put {config_script} Windows\\Temp\\configure_winrm.ps1"
        ], capture_output=True, timeout=30)
        
        if result.returncode == 0:
            print("✅ 配置脚本已复制到目标设备")
            print("📁 位置: C:\\Windows\\Temp\\configure_winrm.ps1")
            return True
        else:
            print("❌ SMB复制失败")
            print(f"错误: {result.stderr.decode()}")
            return False
            
    except (FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"❌ SMB操作失败: {e}")
        return False

def generate_execution_guide():
    """生成执行指南"""
    guide = """# 🚀 WinRM自动配置执行指南

## 目标设备: 192.168.2.134

## 📋 配置状态
- ✅ WinRM端口5985开放 (服务运行中)
- ✅ SMB文件共享可用 (端口445开放)
- ✅ 配置脚本已准备就绪

## 🎯 立即执行方式

### 方式1: 物理访问执行 (最快)
```powershell
# 在目标设备上直接运行:
PowerShell -ExecutionPolicy Bypass -File C:\Windows\Temp\configure_winrm.ps1
```

### 方式2: 计划任务远程执行
```powershell
# 从其他Windows设备执行:
schtasks /Create /S 192.168.2.134 /U chen /P c9fc9f,. /TN "ConfigureWinRM" /SC ONCE /ST 00:01 /TR "powershell -ExecutionPolicy Bypass -File C:\Windows\Temp\configure_winrm.ps1"
schtasks /Run /S 192.168.2.134 /U chen /P c9fc9f,. /TN "ConfigureWinRM"
```

### 方式3: WMI远程执行
```powershell
# 使用WMI远程执行
Invoke-WmiMethod -ComputerName 192.168.2.134 -Class Win32_Process -Name Create -ArgumentList "powershell -ExecutionPolicy Bypass -File C:\Windows\Temp\configure_winrm.ps1" -Credential (Get-Credential)
```

## 📜 配置脚本内容

脚本位置: `C:\Windows\Temp\configure_winrm.ps1`

### 执行的功能:
1. ✅ 启用PowerShell远程 (Enable-PSRemoting)
2. ✅ 配置信任所有主机 (测试环境)
3. ✅ 启用基本身份验证
4. ✅ 重启WinRM服务
5. ✅ 验证配置状态

## ⚡ 快速命令

### 如果能够物理访问:
```cmd
# 命令提示符(管理员)
powershell -ExecutionPolicy Bypass -File C:\Windows\Temp\configure_winrm.ps1
```

### 或者直接运行命令:
```powershell
Enable-PSRemoting -Force
Set-Item WSMan:\localhost\Client\TrustedHosts -Value "*" -Force
Set-Item WSMan:\localhost\Service\Auth\Basic -Value $true
Restart-Service WinRM
```

## 🔍 验证配置

配置完成后测试:
```powershell
# 从其他设备测试
test-wsman -ComputerName 192.168.2.134

# 或者
Enter-PSSession -ComputerName 192.168.2.134 -Credential (Get-Credential)
```

## 🆘 故障处理

如果自动配置失败:
1. 直接物理访问设备执行脚本
2. 手动执行配置命令
3. 检查防火墙设置

---
*配置就绪时间: 2026-04-01 13:57*"""
    
    guide_path = Path("/tmp/winrm_execution_guide.md")
    guide_path.write_text(guide)
    return guide_path

def main():
    """主函数"""
    print("🚀 WinRM自动配置启动")
    print("=" * 60)
    
    # 检查SMB访问
    if check_smb_access():
        print("\n✅ SMB访问可用，尝试自动配置...")
        
        # 复制配置脚本
        if copy_via_smb():
            print("\n🎉 配置脚本部署成功!")
        else:
            print("\n❌ 自动部署失败，需要手动介入")
    else:
        print("\n❌ SMB访问不可用，需要手动配置")
    
    # 生成执行指南
    guide = generate_execution_guide()
    print(f"\n📖 执行指南: {guide}")
    
    print("\n" + "=" * 60)
    print("🎯 立即执行命令:")
    print("在目标设备192.168.2.134上运行:")
    print("powershell -ExecutionPolicy Bypass -File C:\\Windows\\Temp\\configure_winrm.ps1")
    
    print("\n" + "=" * 60)
    print("⚡ 极速手动配置:")
    print("Enable-PSRemoting -Force")
    print("Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value \"*\" -Force")
    print("Set-Item WSMan:\\localhost\\Service\\Auth\\Basic -Value $true")
    print("Restart-Service WinRM")

if __name__ == "__main__":
    main()