$ErrorActionPreference="Stop"
$zipUrl="http://36.250.122.43:8282/api/v1/download?file=python-embed.zip"
$zipPath="C:\temp\python-embed.zip"
$pythonDir="C:\python311"
Write-Output "=== 安装 Python 3.11 ==="
if(!(Test-Path "C:\temp")){New-Item -ItemType Directory -Path "C:\temp" -Force|Out-Null}
Write-Output "[1/3] 下载..."
Invoke-WebRequest -Uri $zipUrl -OutFile $zipPath -UseBasicParsing
Write-Output "[2/3] 解压到 $pythonDir ..."
if(Test-Path $pythonDir){Remove-Item $pythonDir -Recurse -Force}
Expand-Archive $zipPath $pythonDir -Force
Write-Output "[3/3] 设置 PATH..."
$p=[Environment]::GetEnvironmentVariable("Path","Machine")
if($p -notlike "*$pythonDir*"){[Environment]::SetEnvironmentVariable("Path","$p;$pythonDir","Machine")}
$env:Path += ";$pythonDir"
Write-Output "=== 验证 ==="
python --version 2>&1
Remove-Item $zipPath -Force -ErrorAction SilentlyContinue
Write-Output "✅ 安装完成"
