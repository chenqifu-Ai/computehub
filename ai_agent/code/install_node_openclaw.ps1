# install.ps1 - WIN-STD-001: Install Node.js + OpenClaw
# Uses ZIP extraction (not MSI) to avoid msi download truncation via Gateway
$ErrorActionPreference = "Stop"
$logFile = "$env:TEMP\oc_install.log"
function Log($m) { "$(Get-Date -Format HH:mm:ss) $m" | Out-File -Append -Encoding ASCII $logFile; Write-Host $m }

Log "=== Phase 1: Pre-check ==="
$nodeExe = "C:\Program Files\nodejs\node.exe"
$nodeZipDir = "C:\Program Files\nodejs"
$needNode = $true

if (Test-Path $nodeExe) {
    $ver = & $nodeExe --version 2>&1
    if ($LASTEXITCODE -eq 0) { Log "Node.js OK: $ver"; $needNode = $false }
}

if ($needNode) {
    $d = "C:\installers"
    if (-not (Test-Path $d)) { New-Item -ItemType Directory -Path $d -Force | Out-Null }
    Log "Install dir: $d"

    $driveInfo = Get-PSDrive C
    $freeGB = [math]::Round($driveInfo.Free / 1GB, 1)
    Log "C: free: ${freeGB}GB"
    if ($freeGB -lt 2) { throw "Disk space <2GB" }

    Log "=== Phase 2: Download Node.js ZIP (from local Gateway) ==="
    $zip = "$d\nodejs.zip"
    $url = "http://36.250.122.43:8282/api/v1/files/nodejs.zip"
    if (Test-Path $zip) {
        $sz = (Get-Item $zip).Length
        Log "ZIP cached: $([math]::Round($sz/1MB,1))MB"
    } else {
        Log "Downloading Node.js ZIP (36MB)..."
        $wc = New-Object System.Net.WebClient
        $wc.DownloadFile($url, $zip)
        $sz = (Get-Item $zip).Length
        Log "Downloaded: $([math]::Round($sz/1MB,1))MB"
    }

    Log "=== Phase 3: Extract Node.js ZIP ==="
    if (Test-Path $nodeZipDir) {
        # Remove old installation if exists (non-empty)
        Remove-Item "$nodeZipDir\*" -Recurse -Force -ErrorAction SilentlyContinue
    } else {
        New-Item -ItemType Directory -Path $nodeZipDir -Force | Out-Null
    }

    # Check if Expand-Archive is available
    try {
        Expand-Archive -Path $zip -DestinationPath "C:\installers\node-extracted" -Force
        Log "Extracted via Expand-Archive"
    } catch {
        Log "Expand-Archive failed, trying alternative..."
        Add-Type -AssemblyName System.IO.Compression.FileSystem
        [System.IO.Compression.ZipFile]::ExtractToDirectory($zip, "C:\installers\node-extracted")
    }

    # zip contains a subfolder like node-v24.16.0-win-x64\
    $extracted = Get-ChildItem "C:\installers\node-extracted" -Directory | Select-Object -First 1
    if ($extracted) {
        Copy-Item "$($extracted.FullName)\*" "$nodeZipDir\" -Recurse -Force
        Log "Copied from $($extracted.Name) to $nodeZipDir"
    } else {
        Copy-Item "C:\installers\node-extracted\*" "$nodeZipDir\" -Recurse -Force
    }

    # Clean up temp extraction
    Remove-Item "C:\installers\node-extracted" -Recurse -Force -ErrorAction SilentlyContinue

    Log "=== Phase 4: Verify ==="
    if (Test-Path $nodeExe) {
        $ver = & $nodeExe --version
        Log "OK Node.js: $ver"
    } else {
        throw "node.exe not found after extract at $nodeExe"
    }

    # Fix PATH (machine-wide)
    $currPath = [Environment]::GetEnvironmentVariable("Path", "Machine")
    if ($currPath -notlike "*$nodeZipDir*") {
        [Environment]::SetEnvironmentVariable("Path", "$currPath;$nodeZipDir", "Machine")
        Log "PATH updated: $nodeZipDir"
    }
    $env:Path += ";$nodeZipDir"
}

Log "=== Phase 5: Install OpenClaw ==="
$npmExe = "C:\Program Files\nodejs\npm.cmd"
if (-not (Test-Path $npmExe)) { throw "npm.cmd not found at $npmExe" }

$ocExe = "C:\Program Files\nodejs\openclaw.cmd"
if (Test-Path $ocExe) {
    $ver = & $ocExe --version
    Log "OpenClaw OK: $ver"
} else {
    Log "Installing OpenClaw..."
    & $npmExe install -g openclaw@latest 2>&1 | ForEach-Object { Log $_ }
    if ($LASTEXITCODE -ne 0) { throw "npm install openclaw failed ($LASTEXITCODE)" }
    Log "OK OpenClaw installed"
}

Log "=== Phase 6: Final verification ==="
if (Test-Path "C:\Program Files\nodejs\node.exe") {
    Log "OK node: $(& 'C:\Program Files\nodejs\node.exe' --version)"
}
if (Test-Path "C:\Program Files\nodejs\npm.cmd") {
    Log "OK npm: $(& 'C:\Program Files\nodejs\npm.cmd' --version)"
}
$oc = "C:\Program Files\nodejs\openclaw.cmd"
if (Test-Path $oc) {
    Log "OK openclaw: $(& $oc --version)"
} else {
    Log "WARN openclaw.cmd not found (may be in npm global prefix)"
    # Check npm global prefix
    & 'C:\Program Files\nodejs\npm.cmd' root -g 2>&1 | ForEach-Object { Log "npm root -g: $_" }
}
Log "=== ALL DONE ==="