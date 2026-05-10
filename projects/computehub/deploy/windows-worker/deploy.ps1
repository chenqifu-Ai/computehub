# ComputeHub Windows Worker 一键部署脚本
# 在 192.168.1.8 上以管理员 PowerShell 运行

$GATEWAY_URL = "http://192.168.1.17:8282"
$NODE_ID = "win-01"
$DEPLOY_DIR = "C:\computehub"
$BINARY_NAME = "compute-worker-win-amd64.exe"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  ComputeHub Windows Worker 部署" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 创建目录
if (-not (Test-Path $DEPLOY_DIR)) {
    New-Item -ItemType Directory -Path $DEPLOY_DIR | Out-Null
    Write-Host "[1/4] 创建目录: $DEPLOY_DIR" -ForegroundColor Green
} else {
    Write-Host "[1/4] 目录已存在: $DEPLOY_DIR" -ForegroundColor Yellow
}

# 2. 下载二进制
$DOWNLOAD_URL = "$GATEWAY_URL/api/v1/download?file=$BINARY_NAME"
$DEST = "$DEPLOY_DIR\$BINARY_NAME"

if (Test-Path $DEST) {
    Write-Host "[2/4] 二进制已存在，跳过下载" -ForegroundColor Yellow
} else {
    Write-Host "[2/4] 下载二进制: $DOWNLOAD_URL" -ForegroundColor Yellow
    try {
        Invoke-WebRequest -Uri $DOWNLOAD_URL -OutFile $DEST -UseBasicParsing -TimeoutSec 60
        Write-Host "[2/4] 下载完成: $(((Get-Item $DEST).Length / 1MB).ToString('F2')) MB" -ForegroundColor Green
    } catch {
        Write-Host "[2/4] 下载失败: $_" -ForegroundColor Red
        Write-Host "  尝试手动下载:" -ForegroundColor Yellow
        Write-Host "  Start-Process `"$DOWNLOAD_URL`""
        exit 1
    }
}

# 3. 验证下载
$ExpectedSize = 9027072
$ActualSize = (Get-Item $DEST).Length
if ($ActualSize -eq $ExpectedSize) {
    Write-Host "[3/4] 文件大小验证通过: $($ExpectedSize / 1MB) MB" -ForegroundColor Green
} else {
    Write-Host "[3/4] 警告: 文件大小不匹配 (期望: $ExpectedSize, 实际: $ActualSize)" -ForegroundColor Yellow
}

# 4. 启动 Worker
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  即将启动 Worker" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  节点ID: $NODE_ID" -ForegroundColor White
Write-Host "  Gateway: $GATEWAY_URL" -ForegroundColor White
Write-Host "  二进制: $DEST" -ForegroundColor White
Write-Host ""
Write-Host "  按任意键开始，或按 Ctrl+C 取消" -ForegroundColor Yellow
Write-Host ""
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")

# 后台启动
$Process = Start-Process -FilePath $DEST -ArgumentList "--gw", $GATEWAY_URL, "--node-id", $NODE_ID, "--region", "cn-east" -PassThru -WindowStyle Hidden
Write-Host ""
Write-Host "✅ Worker 已启动! PID: $($Process.Id)" -ForegroundColor Green
Write-Host ""
Write-Host "验证命令:" -ForegroundColor Cyan
Write-Host "  curl $GATEWAY_URL/api/v1/nodes/list" -ForegroundColor White
Write-Host ""
Write-Host "查看日志: 打开新的 CMD 窗口执行:" -ForegroundColor Cyan
Write-Host "  tasklist | findstr compute-worker" -ForegroundColor White
Write-Host ""
Write-Host "要停止 Worker:" -ForegroundColor Cyan
Write-Host "  taskkill /F /IM compute-worker-win-amd64.exe" -ForegroundColor White
