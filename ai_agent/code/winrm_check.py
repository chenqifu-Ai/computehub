#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
WinRM连接检查脚本
检查Windows远程管理(WinRM)的可用性
"""

import subprocess

def check_winrm_port():
    """检查WinRM端口连通性"""
    print("🔍 检查WinRM端口(5985)连通性...")
    
    try:
        # 检查端口5985 (WinRM HTTP)
        result = subprocess.run([
            "nc", "-z", "-w", "5", "192.168.2.134", "5985"
        ], capture_output=True, timeout=10)
        
        if result.returncode == 0:
            print("✅ WinRM端口5985开放")
            return True
        else:
            print("❌ WinRM端口5985关闭")
            
            # 检查端口5986 (WinRM HTTPS)
            result_https = subprocess.run([
                "nc", "-z", "-w", "5", "192.168.2.134", "5986"
            ], capture_output=True, timeout=10)
            
            if result_https.returncode == 0:
                print("✅ WinRM HTTPS端口5986开放")
                return True
            else:
                print("❌ WinRM HTTPS端口5986也关闭")
                return False
                
    except FileNotFoundError:
        print("❌ netcat (nc) 工具未安装，无法检查端口")
        return False
    except subprocess.TimeoutExpired:
        print("⏰ 端口检查超时")
        return False

def test_winrm_connection():
    """测试WinRM连接"""
    print("🧪 测试WinRM连接...")
    
    # 尝试PowerShell WinRM连接
    ps_script = """
Try {
    $session = New-PSSession -ComputerName 192.168.2.134 -Credential (Get-Credential) -ErrorAction Stop
    Write-Output "✅ WinRM连接成功!"
    Remove-PSSession $session
} Catch {
    Write-Output "❌ WinRM连接失败: $($_.Exception.Message)"
}
"""
    
    try:
        result = subprocess.run([
            "powershell", "-Command", ps_script
        ], capture_output=True, timeout=30, text=True)
        
        print(result.stdout)
        if "成功" in result.stdout:
            return True
        else:
            return False
            
    except FileNotFoundError:
        print("❌ PowerShell不可用")
        return False
    except subprocess.TimeoutExpired:
        print("⏰ WinRM测试超时")
        return False

def check_winrm_service_status():
    """检查WinRM服务状态"""
    print("📊 检查WinRM服务状态...")
    
    # 尝试远程检查WinRM服务状态
    ps_script = """
Try {
    $service = Get-Service -Name WinRM -ComputerName 192.168.2.134 -ErrorAction Stop
    Write-Output "WinRM服务状态: $($service.Status)"
    Write-Output "启动类型: $($service.StartType)"
} Catch {
    Write-Output "无法获取WinRM服务状态: $($_.Exception.Message)"
}
"""
    
    try:
        result = subprocess.run([
            "powershell", "-Command", ps_script
        ], capture_output=True, timeout=20, text=True)
        
        print(result.stdout)
        
    except FileNotFoundError:
        print("❌ PowerShell不可用")
    except subprocess.TimeoutExpired:
        print("⏰ 服务状态检查超时")

def generate_winrm_setup_guide():
    """生成WinRM设置指南"""
    guide = """# 🪟 WinRM Windows远程管理设置指南

## 目标设备: 192.168.2.134 (Windows)

## 🔧 WinRM启用步骤

### 在目标Windows设备上执行:

#### 方法1: PowerShell命令 (推荐)
```powershell
# 以管理员身份运行PowerShell
Enable-PSRemoting -Force

# 配置信任所有主机 (测试环境)
Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "*" -Force

# 重启WinRM服务
Restart-Service WinRM

# 检查服务状态
Get-Service WinRM
```

#### 方法2: 图形界面设置
```
1. 控制面板 → 系统和安全 → 管理工具
2. 双击"服务"
3. 找到"Windows Remote Management (WS-Management)"
4. 右键 → 属性 → 启动类型: 自动 → 启动
```

#### 方法3: 命令行
```cmd
# 以管理员身份运行CMD
winrm quickconfig

# 如果遇到防火墙提示，输入Y确认
```

## 🛡️ 防火墙配置

### 开放WinRM端口
```powershell
# 允许WinRM HTTP端口(5985)
New-NetFirewallRule -DisplayName "WinRM HTTP" -Direction Inbound -LocalPort 5985 -Protocol TCP -Action Allow

# 允许WinRM HTTPS端口(5986)  
New-NetFirewallRule -DisplayName "WinRM HTTPS" -Direction Inbound -LocalPort 5986 -Protocol TCP -Action Allow
```

### 或者使用高级安全防火墙
```
1. Windows Defender防火墙 → 高级设置
2. 入站规则 → 新建规则
3. 端口 → TCP 5985,5986 → 允许连接
```

## 🧪 连接测试

### 从其他设备测试连接
```powershell
# 测试WinRM连接
test-wsman -ComputerName 192.168.2.134

# PowerShell远程连接
Enter-PSSession -ComputerName 192.168.2.134 -Credential (Get-Credential)
```

### 检查WinRM配置
```powershell
# 查看WinRM配置
winrm get winrm/config

# 查看监听器
winrm enumerate winrm/config/listener
```

## ⚙️ 高级配置

### 启用基本身份验证
```powershell
# 启用基本身份验证 (测试用)
Set-Item WSMan:\\localhost\\Service\\Auth\\Basic -Value $true
```

### 配置SSL证书
```powershell
# 创建自签名证书
$cert = New-SelfSignedCertificate -DnsName $env:COMPUTERNAME -CertStoreLocation Cert:\\LocalMachine\\My

# 创建HTTPS监听器
winrm create winrm/config/Listener?Address=*+Transport=HTTPS @{Hostname=$env:COMPUTERNAME; CertificateThumbprint=$cert.Thumbprint}
```

## 🔍 故障排除

### 常见问题解决
```powershell
# 重置WinRM配置
winrm delete winrm/config/listener?Address=*+Transport=HTTP
winrm delete winrm/config/listener?Address=*+Transport=HTTPS
winrm quickconfig

# 检查错误日志
get-eventlog -LogName Microsoft-Windows-WinRM/Operational -Newest 10
```

### 网络问题
- 确保网络连通性: `Test-NetConnection 192.168.2.134 -Port 5985`
- 检查防火墙规则
- 确认网络配置文件为"专用"

## 🚀 快速启用命令

**在目标设备上以管理员运行:**
```powershell
Enable-PSRemoting -Force; Set-Item WSMan:\\localhost\\Client\\TrustedHosts -Value "*" -Force; Restart-Service WinRM
```

---
*WinRM是强大的Windows远程管理工具，比RDP更轻量，适合命令行管理*"""
    
    guide_path = "/tmp/winrm_setup_guide.md"
    with open(guide_path, 'w', encoding='utf-8') as f:
        f.write(guide)
    
    return guide_path

def main():
    """主函数"""
    print("🪟 WinRM连接检查")
    print("=" * 50)
    print("目标设备: 192.168.2.134")
    print("=" * 50)
    
    # 检查端口连通性
    port_open = check_winrm_port()
    
    print("\n" + "=" * 50)
    
    # 如果端口开放，测试连接
    if port_open:
        print("🔗 端口开放，测试WinRM连接...")
        connection_ok = test_winrm_connection()
        
        if connection_ok:
            print("🎉 WinRM连接可用!")
        else:
            print("❌ WinRM连接测试失败")
            check_winrm_service_status()
    else:
        print("❌ WinRM端口未开放")
        print("💡 需要在目标设备启用WinRM")
    
    # 生成设置指南
    guide_path = generate_winrm_setup_guide()
    print(f"\n📖 WinRM设置指南: {guide_path}")
    
    print("\n" + "=" * 50)
    print("🎯 结论:")
    if port_open:
        print("✅ WinRM端口开放，但需要配置身份验证")
    else:
        print("❌ WinRM未启用，需要先在目标设备设置")
    
    print("\n⚡ 快速启用命令 (在目标设备运行):")
    print("powershell -Command \"Enable-PSRemoting -Force; Set-Item WSMan:\\\\localhost\\\\Client\\\\TrustedHosts -Value '*' -Force\"")

if __name__ == "__main__":
    main()