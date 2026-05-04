# WinRM 管理员配置脚本
# 必须在目标设备 192.168.2.134 上以管理员身份运行

Write-Host "🔧 以管理员身份配置WinRM..." -ForegroundColor Yellow

# 检查管理员权限
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ 请以管理员身份运行此脚本!" -ForegroundColor Red
    Write-Host "   右键点击PowerShell，选择'以管理员身份运行'" -ForegroundColor Yellow
    exit 1
}

Write-Host "✅ 当前具有管理员权限" -ForegroundColor Green

# 1. 启用WinRM服务
Write-Host "1. 启用WinRM服务..." -ForegroundColor Green
Enable-PSRemoting -Force

# 2. 配置基本身份验证
Write-Host "2. 启用基本身份验证..." -ForegroundColor Green
Set-Item -Path "WSMan:\localhost\Service\Auth\Basic" -Value $true

# 3. 配置信任主机
Write-Host "3. 配置信任主机..." -ForegroundColor Green
Set-Item -Path "WSMan:\localhost\Client\TrustedHosts" -Value "*" -Force

# 4. 配置服务自动启动
Write-Host "4. 设置服务自动启动..." -ForegroundColor Green
Set-Service -Name "WinRM" -StartupType Automatic
Start-Service -Name "WinRM"

# 5. 配置防火墙规则
Write-Host "5. 配置防火墙允许WinRM..." -ForegroundColor Green
netsh advfirewall firewall add rule name="WinRM HTTP" dir=in action=allow protocol=TCP localport=5985
netsh advfirewall firewall add rule name="WinRM HTTPS" dir=in action=allow protocol=TCP localport=5986

# 6. 设置执行策略
Write-Host "6. 设置执行策略..." -ForegroundColor Green
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Force

# 7. 验证用户权限
Write-Host "7. 验证用户权限..." -ForegroundColor Green
$user = "chen"
$isAdmin = (Get-LocalGroupMember -Group "Administrators" | Where-Object {$_.Name -like "*$user*"})
if ($isAdmin) {
    Write-Host "   ✅ 用户 '$user' 是管理员" -ForegroundColor Green
} else {
    Write-Host "   ⚠️  用户 '$user' 不是管理员，正在添加..." -ForegroundColor Yellow
    Add-LocalGroupMember -Group "Administrators" -Member "$user"
    Write-Host "   ✅ 已添加用户 '$user' 到管理员组" -ForegroundColor Green
}

# 8. 验证配置
Write-Host "8. 验证配置..." -ForegroundColor Green
Write-Host "   WinRM服务状态: " -NoNewline
$service = Get-Service -Name "WinRM"
if ($service.Status -eq "Running") {
    Write-Host "✅ 运行中" -ForegroundColor Green
} else {
    Write-Host "❌ 未运行" -ForegroundColor Red
}

Write-Host "   基本认证启用: " -NoNewline
$basicAuth = Get-Item -Path "WSMan:\localhost\Service\Auth\Basic"
if ($basicAuth.Value -eq $true) {
    Write-Host "✅ 已启用" -ForegroundColor Green
} else {
    Write-Host "❌ 未启用" -ForegroundColor Red
}

Write-Host "   端口监听状态:" -ForegroundColor White
netstat -an | findstr ":5985"

# 9. 测试配置
Write-Host "9. 测试WinRM连接..." -ForegroundColor Green
Try {
    $result = Test-WSMan -ComputerName localhost
    Write-Host "   ✅ WinRM配置成功!" -ForegroundColor Green
    Write-Host "   Product: $($result.ProductVersion)" -ForegroundColor White
    Write-Host "   Protocol: $($result.ProtocolVersion)" -ForegroundColor White
} Catch {
    Write-Host "   ❌ WinRM测试失败: $_" -ForegroundColor Red
}

Write-Host ""
Write-Host "🎉 WinRM管理员配置完成!" -ForegroundColor Green
Write-Host "现在可以从远程设备使用以下凭据连接:" -ForegroundColor Cyan
Write-Host "   计算机: 192.168.2.134" -ForegroundColor White
Write-Host "   端口: 5985" -ForegroundColor White
Write-Host "   用户名: chen" -ForegroundColor White
Write-Host "   密码: c9fc9f,." -ForegroundColor White

Write-Host ""
Write-Host "🚀 下一步: 安装OpenClaw" -ForegroundColor Magenta
Write-Host "   在远程会话中执行: npm install -g openclaw" -ForegroundColor White