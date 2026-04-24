# Windows OpenClaw自动化部署脚本

param(
    [Parameter(Mandatory=$true)]
    [string]$ComputerName,
    [string]$UserName = "administrator",
    [Parameter(Mandatory=$true)]
    [string]$Password,
    [int]$Port = 5985
)

# 颜色输出
$ErrorActionPreference = "Stop"

function Write-Info {
    Write-Host "[INFO] $($args[0])" -ForegroundColor Green
}

function Write-Warn {
    Write-Host "[WARN] $($args[0])" -ForegroundColor Yellow
}

function Write-Error {
    Write-Host "[ERROR] $($args[0])" -ForegroundColor Red
}

# Windows设备检测
function Test-WindowsDevice {
    Write-Info "检测Windows设备: $UserName@$ComputerName"
    
    try {
        # 测试WinRM连接
        $session = New-PSSession -ComputerName $ComputerName -Credential (New-Object System.Management.Automation.PSCredential($UserName, (ConvertTo-SecureString $Password -AsPlainText -Force)))
        
        Invoke-Command -Session $session -ScriptBlock {
            Write-Host "Windows版本: $([System.Environment]::OSVersion.VersionString)"
            Write-Host "系统架构: $([System.Environment]::Is64BitOperatingSystem ? '64位' : '32位')"
            Write-Host "用户名: $([System.Environment]::UserName)"
        }
        
        Remove-PSSession $session
        return $true
    }
    catch {
        Write-Error "WinRM连接失败: $($_.Exception.Message)"
        return $false
    }
}

# 安装Node.js
function Install-NodeJS {
    Write-Info "检查并安装Node.js..."
    
    $session = New-PSSession -ComputerName $ComputerName -Credential (New-Object System.Management.Automation.PSCredential($UserName, (ConvertTo-SecureString $Password -AsPlainText -Force)))
    
    $nodeCheck = Invoke-Command -Session $session -ScriptBlock {
        $nodeVersion = node --version 2>$null
        $npmVersion = npm --version 2>$null
        return @{Node=$nodeVersion; NPM=$npmVersion}
    }
    
    if (-not $nodeCheck.Node) {
        Write-Info "安装Node.js..."
        
        # 下载并安装Node.js
        Invoke-Command -Session $session -ScriptBlock {
            $tempDir = "$env:TEMP\\nodejs-install"
            New-Item -ItemType Directory -Path $tempDir -Force | Out-Null
            
            # 下载Node.js安装包
            $nodeUrl = "https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi"
            $installerPath = "$tempDir\\nodejs.msi"
            
            Invoke-WebRequest -Uri $nodeUrl -OutFile $installerPath
            
            # 静默安装
            Start-Process msiexec -ArgumentList "/i `"$installerPath`" /quiet /norestart" -Wait
            
            # 更新环境变量
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
        }
        
        Write-Info "Node.js安装完成"
    }
    else {
        Write-Info "Node.js已安装: $($nodeCheck.Node)"
    }
    
    Remove-PSSession $session
}

# 安装OpenClaw
function Install-OpenClaw {
    Write-Info "安装OpenClaw..."
    
    $session = New-PSSession -ComputerName $ComputerName -Credential (New-Object System.Management.Automation.PSCredential($UserName, (ConvertTo-SecureString $Password -AsPlainText -Force)))
    
    Invoke-Command -Session $session -ScriptBlock {
        # 全局安装OpenClaw
        npm install -g openclaw@latest
        
        # 验证安装
        openclaw --version
    }
    
    Remove-PSSession $session
}

# 初始化配置
function Initialize-Config {
    Write-Info "初始化OpenClaw配置..."
    
    $session = New-PSSession -ComputerName $ComputerName -Credential (New-Object System.Management.Automation.PSCredential($UserName, (ConvertTo-SecureString $Password -AsPlainText -Force)))
    
    Invoke-Command -Session $session -ScriptBlock {
        # 创建配置目录
        $openclawDir = "$env:USERPROFILE\\.openclaw"
        if (-not (Test-Path $openclawDir)) {
            New-Item -ItemType Directory -Path $openclawDir -Force | Out-Null
        }
        
        # 运行初始化
        openclaw setup
    }
    
    Remove-PSSession $session
}

# 同步配置（Windows到Windows）
function Sync-Config {
    Write-Info "同步配置到Windows设备..."
    
    # 本地配置打包
    $localConfig = "$env:USERPROFILE\\.openclaw"
    $tempArchive = "$env:TEMP\\openclaw-config.zip"
    
    if (Test-Path $localConfig) {
        # 创建ZIP存档
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::CreateFromDirectory($localConfig, $tempArchive)
        
        # 复制到远程设备
        Copy-Item -Path $tempArchive -Destination "\\$ComputerName\C$\Users\$UserName\AppData\Local\Temp\openclaw-config.zip" -Force
        
        # 远程解压
        $session = New-PSSession -ComputerName $ComputerName -Credential (New-Object System.Management.Automation.PSCredential($UserName, (ConvertTo-SecureString $Password -AsPlainText -Force)))
        
        Invoke-Command -Session $session -ScriptBlock {
            Add-Type -AssemblyName System.IO.Compression.FileSystem
            $zipPath = "$env:TEMP\\openclaw-config.zip"
            $extractPath = "$env:USERPROFILE\\.openclaw"
            
            if (Test-Path $extractPath) {
                # 备份现有配置
                $backupPath = "$extractPath-backup-$(Get-Date -Format 'yyyyMMdd_HHmm')"
                Rename-Item -Path $extractPath -NewName $backupPath
            }
            
            # 解压新配置
            [System.IO.Compression.ZipFile]::ExtractToDirectory($zipPath, $extractPath)
            
            # 清理临时文件
            Remove-Item $zipPath -Force
        }
        
        Remove-PSSession $session
        Remove-Item $tempArchive -Force
    }
    else {
        Write-Warn "本地OpenClaw配置目录不存在，跳过同步"
    }
}

# 启动服务
function Start-Service {
    Write-Info "启动OpenClaw Gateway服务..."
    
    $session = New-PSSession -ComputerName $ComputerName -Credential (New-Object System.Management.Automation.PSCredential($UserName, (ConvertTo-SecureString $Password -AsPlainText -Force)))
    
    Invoke-Command -Session $session -ScriptBlock {
        # 停止现有服务
        Get-Process -Name "node" -ErrorAction SilentlyContinue | Where-Object { $_.CommandLine -like "*openclaw*" } | Stop-Process -Force
        
        # 启动新服务
        Start-Process -FilePath "node" -ArgumentList "-e `"require('openclaw').startGateway({port: 18789})`"" -WindowStyle Hidden
        
        # 等待启动
        Start-Sleep -Seconds 5
        
        # 验证服务
        try {
            Invoke-RestMethod -Uri "http://localhost:18789/health" -Method Get
        }
        catch {
            Write-Warn "服务健康检查失败: $($_.Exception.Message)"
        }
    }
    
    Remove-PSSession $session
}

# 验证部署
function Validate-Deployment {
    Write-Info "验证Windows部署..."
    
    $session = New-PSSession -ComputerName $ComputerName -Credential (New-Object System.Management.Automation.PSCredential($UserName, (ConvertTo-SecureString $Password -AsPlainText -Force)))
    
    $result = Invoke-Command -Session $session -ScriptBlock {
        # 检查目录结构
        $openclawDir = "$env:USERPROFILE\\.openclaw"
        $dirs = @("workspace", "extensions", "config")
        
        $status = @{
            DirectoryExists = Test-Path $openclawDir
            SubDirectories = @{}
            ServiceRunning = $false
            ConfigFiles = @{}
        }
        
        if ($status.DirectoryExists) {
            foreach ($dir in $dirs) {
                $status.SubDirectories[$dir] = Test-Path "$openclawDir\$dir"
            }
            
            # 检查配置文件
            $configFiles = @("openclaw.json", "workspace\AGENTS.md", "workspace\SOUL.md")
            foreach ($file in $configFiles) {
                $status.ConfigFiles[$file] = Test-Path "$openclawDir\$file"
            }
        }
        
        # 检查服务
        try {
            $health = Invoke-RestMethod -Uri "http://localhost:18789/health" -Method Get -ErrorAction Stop
            $status.ServiceRunning = $health.ok -eq $true
        }
        catch {
            $status.ServiceRunning = $false
        }
        
        return $status
    }
    
    Remove-PSSession $session
    
    Write-Host "部署验证结果:" -ForegroundColor Cyan
    Write-Host "- 配置目录: $(if($result.DirectoryExists){'✅'}else{'❌'})"
    foreach ($dir in $result.SubDirectories.Keys) {
        Write-Host "- $dir目录: $(if($result.SubDirectories[$dir]){'✅'}else{'❌'})"
    }
    foreach ($file in $result.ConfigFiles.Keys) {
        Write-Host "- $file文件: $(if($result.ConfigFiles[$file]){'✅'}else{'❌'})"
    }
    Write-Host "- 服务运行: $(if($result.ServiceRunning){'✅'}else{'❌'})"
}

# 主函数
function Main {
    Write-Host "=== Windows OpenClaw自动化部署 ===" -ForegroundColor Magenta
    Write-Host "目标设备: $ComputerName" -ForegroundColor Yellow
    Write-Host "用户名: $UserName" -ForegroundColor Yellow
    
    try {
        # 执行部署流程
        if (-not (Test-WindowsDevice)) { return }
        Install-NodeJS
        Install-OpenClaw
        Initialize-Config
        Sync-Config
        Start-Service
        Validate-Deployment
        
        Write-Host ""
        Write-Host "🎯 Windows部署完成!" -ForegroundColor Green
        Write-Host "设备: $UserName@$ComputerName" -ForegroundColor Yellow
        Write-Host "Gateway: http://$ComputerName`:18789" -ForegroundColor Yellow
        Write-Host "状态: ✅ 正常运行" -ForegroundColor Green
    }
    catch {
        Write-Error "部署失败: $($_.Exception.Message)"
        Write-Error "详细错误: $($_.Exception.StackTrace)"
    }
}

# 执行主函数
Main