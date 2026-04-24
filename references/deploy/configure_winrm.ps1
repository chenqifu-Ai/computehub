# WinRM 配置脚本
# 在目标设备 192.168.2.134 上运行此脚本

Write-Host "🔧 配置WinRM远程管理..." -ForegroundColor Yellow

# 1. 启用WinRM服务
Write-Host "1. 启用WinRM服务..." -ForegroundColor Green
Enable-PSRemoting -Force

# 2. 设置WinRM为自动启动
Write-Host "2. 设置服务自动启动..." -ForegroundColor Green
Set-Service -Name "WinRM" -StartupType Automatic
Start-Service -Name "WinRM"

# 3. 配置基本身份验证
Write-Host "3. 配置基本身份验证..." -ForegroundColor Green
Set-Item -Path "WSMan:\localhost\Service\Auth\Basic" -Value $true

# 4. 允许远程连接
Write-Host "4. 允许远程连接..." -ForegroundColor Green
Set-Item -Path "WSMan:\localhost\Client\TrustedHosts" -Value "*" -Force

# 5. 配置防火墙规则
Write-Host "5. 配置防火墙..." -ForegroundColor Green
netsh advfirewall firewall add rule name="WinRM HTTP" dir=in action=allow protocol=TCP localport=5985
netsh advfirewall firewall add rule name="WinRM HTTPS" dir=in action=allow protocol=TCP localport=5986

# 6. 设置执行策略
Write-Host "6. 设置执行策略..." -ForegroundColor Green
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force

# 7. 创建测试用户（如果不存在）
Write-Host "7. 检查用户配置..." -ForegroundColor Green
$userExists = Get-LocalUser -Name "chen" -ErrorAction SilentlyContinue
if (-not $userExists) {
    Write-Host "  创建用户chen..." -ForegroundColor Yellow
    $password = ConvertTo-SecureString "c9fc9f,." -AsPlainText -Force
    New-LocalUser -Name "chen" -Password $password -FullName "OpenClaw User" -Description "OpenClaw部署用户"
    Add-LocalGroupMember -Group "Administrators" -Member "chen"
}

# 8. 验证配置
Write-Host "8. 验证配置..." -ForegroundColor Green
Write-Host "   WinRM服务状态:" -ForegroundColor White
Get-Service -Name "WinRM" | Format-Table Name, Status, StartType

Write-Host "   监听端口:" -ForegroundColor White
netstat -an | findstr ":5985"

Write-Host "   认证配置:" -ForegroundColor White
Get-ChildItem "WSMan:\localhost\Service\Auth"

Write-Host ""
Write-Host "✅ WinRM配置完成！" -ForegroundColor Green
Write-Host "现在可以从其他设备通过WinRM远程管理此计算机" -ForegroundColor Cyan
Write-Host "用户名: chen" -ForegroundColor Cyan
Write-Host "密码: c9fc9f,." -ForegroundColor Cyan
Write-Host "端口: 5985" -ForegroundColor Cyan

# 测试命令
Write-Host ""
Write-Host "🧪 测试本地WinRM:" -ForegroundColor Yellow
Try {
    $result = Invoke-Command -ComputerName localhost -ScriptBlock { 
        "测试成功！当前用户: $env:USERNAME, 计算机名: $env:COMPUTERNAME" 
    } -Credential (Get-Credential -UserName "chen" -Message "输入密码")
    Write-Host "   ✅ " $result -ForegroundColor Green
} Catch {
    Write-Host "   ❌ 测试失败: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "📋 下一步:" -ForegroundColor Magenta
Write-Host "   1. 保存此脚本在目标设备上运行" -ForegroundColor White
Write-Host "   2. 配置完成后尝试远程连接" -ForegroundColor White
Write-Host "   3. 安装OpenClaw: npm install -g openclaw" -ForegroundColor White