# 🚀 WinRM 配置和 OpenClaw 部署指南

## 📋 目标设备信息
- **IP地址**: 192.168.2.134
- **用户名**: chen
- **密码**: c9fc9f,.
- **当前状态**: WinRM端口开放但需要身份验证配置

## 🔧 配置步骤

### 步骤1: 在目标设备上配置WinRM

**方法A: 使用PowerShell脚本**
1. 远程桌面连接到 192.168.2.134
2. 以管理员身份打开PowerShell
3. 运行配置脚本:
   ```powershell
   # 下载或复制配置脚本
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/your-repo/configure_winrm.ps1" -OutFile "configure_winrm.ps1"
   
   # 执行配置
   .\configure_winrm.ps1
   ```

**方法B: 手动配置**
```powershell
# 1. 启用WinRM
Enable-PSRemoting -Force

# 2. 允许基本认证
Set-Item -Path "WSMan:\localhost\Service\Auth\Basic" -Value $true

# 3. 信任所有主机
Set-Item -Path "WSMan:\localhost\Client\TrustedHosts" -Value "*" -Force

# 4. 配置防火墙
netsh advfirewall firewall add rule name="WinRM HTTP" dir=in action=allow protocol=TCP localport=5985

# 5. 设置执行策略
Set-ExecutionPolicy RemoteSigned -Force
```

### 步骤2: 验证配置
```powershell
# 检查服务状态
Get-Service WinRM

# 测试本地连接
Test-WSMan -ComputerName localhost

# 检查认证设置
Get-ChildItem WSMan:\localhost\Service\Auth
```

### 步骤3: 安装OpenClaw
```powershell
# 1. 安装Node.js (如果未安装)
winget install OpenJS.NodeJS.LTS

# 2. 安装OpenClaw
npm install -g openclaw

# 3. 验证安装
openclaw --version
```

## 🎯 远程部署命令

配置完成后，可以从其他设备执行:

```powershell
# 建立远程会话
$cred = Get-Credential -UserName "chen" -Message "输入密码"
Enter-PSSession -ComputerName 192.168.2.134 -Credential $cred

# 在远程会话中安装
npm install -g openclaw
openclaw init
```

## ⚠️ 常见问题

### 问题1: 401未授权错误
**解决方法**:
- 确保基本身份验证已启用
- 检查用户凭据是否正确
- 验证用户是否有管理员权限

### 问题2: 连接被拒绝
**解决方法**:
- 检查WinRM服务是否运行
- 验证防火墙设置
- 确认端口5985开放

### 问题3: 执行策略限制
**解决方法**:
```powershell
Set-ExecutionPolicy RemoteSigned -Force
```

## 🔒 安全建议

1. **限制信任主机**: 生产环境中不要使用 `*`
2. **使用HTTPS**: 配置WinRM over HTTPS (端口5986)
3. **证书认证**: 使用证书代替基本认证
4. **网络隔离**: 在受信任的网络中使用

## 📞 支持信息

- **WinRM文档**: https://docs.microsoft.com/en-us/windows/win32/winrm/portal
- **OpenClaw文档**: https://docs.openclaw.ai
- **故障排除**: 检查事件查看器中的WinRM日志

---
*生成时间: 2026-04-02 15:12*
*适用于: Windows设备远程部署*