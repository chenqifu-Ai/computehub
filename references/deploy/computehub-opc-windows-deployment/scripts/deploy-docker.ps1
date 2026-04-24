# ComputeHub-OPC Docker部署脚本
# 适用于Windows生产环境

Write-Host "🚀 开始部署 ComputeHub-OPC v1.0.0 (Docker方式)" -ForegroundColor Green

# 检查Docker是否安装
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Docker未安装，正在安装Docker Desktop..." -ForegroundColor Red
    
    # 安装Docker Desktop
    winget install --id Docker.DockerDesktop -e --accept-package-agreements --accept-source-agreements
    
    Write-Host "✅ Docker安装完成，请重启计算机后重新运行此脚本" -ForegroundColor Green
    exit 1
}

# 检查Docker服务状态
try {
    $dockerInfo = docker info 2>$null
    if ($LASTEXITCODE -ne 0) {
        Write-Host "❌ Docker服务未运行，正在启动..." -ForegroundColor Red
        Start-Service Docker
        Start-Sleep -Seconds 10
    }
} catch {
    Write-Host "❌ Docker服务异常: $_" -ForegroundColor Red
    exit 1
}

Write-Host "✅ Docker状态正常" -ForegroundColor Green

# 创建部署目录
$deployDir = "$env:USERPROFILE\ComputeHub-OPC"
if (-not (Test-Path $deployDir)) {
    New-Item -ItemType Directory -Path $deployDir -Force | Out-Null
}
Set-Location $deployDir

Write-Host "📁 部署目录: $deployDir" -ForegroundColor Yellow

# 创建Docker compose文件
$dockerComposeContent = @"
version: '3.8'

services:
  computehub-opc:
    image: computehub/opc-server:v1.0.0
    container_name: computehub-opc-server
    ports:
      - "4840:4840"  # OPC UA端口
      - "8080:8080"  # 管理界面
      - "5000:5000"  # 健康检查
    environment:
      - ASPNETCORE_ENVIRONMENT=Production
      - OPC__MaxSessions=50
      - OPC__PublishingInterval=1000
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
    networks:
      - computehub-network

  monitor:
    image: prom/prometheus:latest
    container_name: computehub-monitor
    ports:
      - "9090:9090"
    volumes:
      - ./monitor/prometheus.yml:/etc/prometheus/prometheus.yml
      - ./monitor/data:/prometheus
    restart: unless-stopped
    networks:
      - computehub-network

networks:
  computehub-network:
    driver: bridge
"@

Set-Content -Path "docker-compose.yml" -Value $dockerComposeContent

# 创建Prometheus配置目录
New-Item -ItemType Directory -Path "./monitor" -Force | Out-Null

# Prometheus配置
$prometheusConfig = @"
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'computehub-opc'
    static_configs:
      - targets: ['computehub-opc:5000']
    metrics_path: '/metrics'

  - job_name: 'node-exporter'
    static_configs:
      - targets: ['host.docker.internal:9100']
"@

Set-Content -Path "./monitor/prometheus.yml" -Value $prometheusConfig

# 创建数据目录
New-Item -ItemType Directory -Path "./data" -Force | Out-Null
New-Item -ItemType Directory -Path "./logs" -Force | Out-Null

Write-Host "📋 配置文件创建完成" -ForegroundColor Green

# 拉取镜像并启动服务
Write-Host "🐳 拉取Docker镜像..." -ForegroundColor Yellow
try {
    docker-compose pull
} catch {
    Write-Host "⚠️  镜像拉取失败，尝试直接启动..." -ForegroundColor Yellow
}

Write-Host "🚀 启动ComputeHub-OPC服务..." -ForegroundColor Green
docker-compose up -d

# 等待服务启动
Write-Host "⏳ 等待服务启动(10秒)..." -ForegroundColor Yellow
Start-Sleep -Seconds 10

# 检查服务状态
Write-Host "🔍 检查服务状态..." -ForegroundColor Yellow

try {
    $opcStatus = docker ps --filter "name=computehub-opc-server" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    $monitorStatus = docker ps --filter "name=computehub-monitor" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    
    Write-Host ""
    Write-Host "📊 服务状态:" -ForegroundColor Cyan
    Write-Host $opcStatus
    Write-Host $monitorStatus
    
    # 测试健康检查
    $healthResponse = Invoke-WebRequest -Uri "http://localhost:5000/health" -UseBasicParsing -ErrorAction SilentlyContinue
    if ($healthResponse.StatusCode -eq 200) {
        Write-Host "✅ 健康检查: 通过" -ForegroundColor Green
    } else {
        Write-Host "⚠️  健康检查: 待验证" -ForegroundColor Yellow
    }
    
} catch {
    Write-Host "❌ 服务状态检查失败: $_" -ForegroundColor Red
}

# 配置防火墙
Write-Host "🔥 配置防火墙规则..." -ForegroundColor Yellow
try {
    # 开放OPC UA端口
    New-NetFirewallRule -DisplayName "ComputeHub-OPC OPC UA" -Direction Inbound -LocalPort 4840 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
    
    # 开放管理界面端口  
    New-NetFirewallRule -DisplayName "ComputeHub-OPC Web Console" -Direction Inbound -LocalPort 8080 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
    
    # 开放监控端口
    New-NetFirewallRule -DisplayName "ComputeHub-OPC Monitoring" -Direction Inbound -LocalPort 9090 -Protocol TCP -Action Allow -ErrorAction SilentlyContinue
    
    Write-Host "✅ 防火墙规则配置完成" -ForegroundColor Green
} catch {
    Write-Host "⚠️  防火墙配置可能需要管理员权限" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "🎉 ComputeHub-OPC部署完成!" -ForegroundColor Green
Write-Host ""
Write-Host "📊 访问地址:" -ForegroundColor Cyan
Write-Host "  管理界面: http://localhost:8080"
Write-Host "  OPC UA端点: opc.tcp://localhost:4840"
Write-Host "  监控面板: http://localhost:9090"
Write-Host "  健康检查: http://localhost:5000/health"
Write-Host ""
Write-Host "📋 常用命令:" -ForegroundColor Cyan
Write-Host "  查看日志: docker-compose logs -f"
Write-Host "  停止服务: docker-compose down"
Write-Host "  重启服务: docker-compose restart"
Write-Host "  更新配置: 修改 docker-compose.yml 后运行 docker-compose up -d"
Write-Host ""
Write-Host "⚠️  注意事项:" -ForegroundColor Yellow
Write-Host "  - 首次访问可能需要等待1-2分钟服务完全启动"
Write-Host "  - 确保端口4840、8080、9090未被其他程序占用"
Write-Host "  - 生产环境建议配置SSL证书"

# 创建快捷脚本
Set-Content -Path "start.ps1" -Value "docker-compose up -d"
Set-Content -Path "stop.ps1" -Value "docker-compose down"
Set-Content -Path "logs.ps1" -Value "docker-compose logs -f"

Write-Host "✅ 部署脚本完成!" -ForegroundColor Green