# OpenClaw Windows一键部署解决方案

Write-Host "🎯 OpenClaw Windows自动化部署" -ForegroundColor Magenta
Write-Host "==========================================" -ForegroundColor Cyan

# 检查管理员权限
if (-NOT ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole] "Administrator")) {
    Write-Host "❌ 请以管理员身份运行此脚本" -ForegroundColor Red
    Write-Host "💡 右键点击 - 以管理员身份运行" -ForegroundColor Yellow
    pause
    exit 1
}

Write-Host "✅ 管理员权限验证通过" -ForegroundColor Green

# 部署函数
function Install-OpenClaw {
    param($StepName, $Command)
    
    Write-Host ""
    Write-Host "🚀 $StepName" -ForegroundColor Yellow
    Write-Host "命令: $Command" -ForegroundColor Gray
    
    try {
        $result = Invoke-Expression $Command 2>&1
        Write-Host "✅ 完成" -ForegroundColor Green
        if ($result) { Write-Host $result -ForegroundColor White }
        return $true
    }
    catch {
        Write-Host "❌ 失败: $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

# 主部署流程
Write-Host ""
Write-Host "开始部署流程..." -ForegroundColor Cyan

# 1. 检查Node.js
if (-not (Install-OpenClaw "检查Node.js" "node --version")) {
    Write-Host ""
    Write-Host "❌ Node.js未安装" -ForegroundColor Red
    Write-Host "请从 https://nodejs.org 下载并安装Node.js" -ForegroundColor Yellow
    Write-Host "安装完成后重新运行此脚本" -ForegroundColor Yellow
    pause
    exit 1
}

# 2. 安装OpenClaw
if (-not (Install-OpenClaw "安装OpenClaw" "npm install -g openclaw@latest")) {
    Write-Host ""
    Write-Host "❌ OpenClaw安装失败" -ForegroundColor Red
    Write-Host "请检查网络连接或npm配置" -ForegroundColor Yellow
    pause
    exit 1
}

# 3. 初始化配置
if (-not (Install-OpenClaw "初始化配置" "openclaw setup")) {
    Write-Host ""
    Write-Host "⚠️  配置初始化可能有警告，继续执行..." -ForegroundColor Yellow
}

# 4. 启动服务
Write-Host ""
Write-Host "🚀 启动OpenClaw服务..." -ForegroundColor Yellow

# 停止现有服务
Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*openclaw*" } | Stop-Process -Force

# 启动新服务
Start-Process -FilePath "node" -ArgumentList "-e `"require('openclaw').startGateway({port: 18789})`"" -WindowStyle Hidden

Write-Host "✅ 服务启动命令已发送" -ForegroundColor Green
Write-Host "等待服务启动..." -ForegroundColor Yellow
Start-Sleep -Seconds 5

# 5. 验证部署
Write-Host ""
Write-Host "✅ 验证部署结果..." -ForegroundColor Cyan

try {
    $health = Invoke-RestMethod -Uri "http://localhost:18789/health" -Method Get -ErrorAction Stop
    
    if ($health.ok) {
        Write-Host "🎉 OpenClaw部署成功!" -ForegroundColor Green
        Write-Host "📍 本地访问: http://localhost:18789" -ForegroundColor Cyan
        
        # 获取本机IP
        $ip = (Get-NetIPAddress | Where-Object { 
            $_.AddressFamily -eq 'IPv4' -and $_.IPAddress -ne '127.0.0.1' -and $_.IPAddress -notlike '169.254.*'
        } | Select-Object -First 1).IPAddress
        
        Write-Host "🌐 远程访问: http://$ip`:18789" -ForegroundColor Cyan
        Write-Host "📊 服务状态: $($health.status)" -ForegroundColor White
    }
    else {
        Write-Host "❌ 服务健康检查异常" -ForegroundColor Red
    }
}
catch {
    Write-Host "❌ 服务验证失败: $($_.Exception.Message)" -ForegroundColor Red
    Write-Host "💡 请手动检查服务状态" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "部署完成!" -ForegroundColor Magenta
Write-Host ""
Write-Host "下一步操作:" -ForegroundColor Yellow
Write-Host "• 检查防火墙设置" -ForegroundColor White
Write-Host "• 测试远程访问" -ForegroundColor White
Write-Host "• 配置所需技能" -ForegroundColor White
Write-Host ""
pause