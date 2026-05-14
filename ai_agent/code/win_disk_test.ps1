
$testDir = "D:\testdisk"
$testFile = Join-Path $testDir "testfile.bin"
if (-not (Test-Path $testDir)) { New-Item -ItemType Directory -Path $testDir -Force | Out-Null }

Write-Host "=== Disk Write Test ==="
$stopwatch = [System.Diagnostics.Stopwatch]::StartNew()
$data = New-Object byte[] 10485760
(New-Object Security.Cryptography.RNGCryptoServiceProvider).GetBytes($data)
$stream = [System.IO.File]::OpenWrite($testFile)
for ($i = 0; $i -lt 5; $i++) { $stream.Write($data, 0, $data.Length) }
$stream.Close()
$stopwatch.Stop()
$writeMs = $stopwatch.ElapsedMilliseconds
Write-Host "50MB sequential write: ${writeMs}ms"

Write-Host ""
Write-Host "=== Disk Read Test ==="
$stopwatch.Reset()
$stopwatch.Start()
$rstream = [System.IO.File]::OpenRead($testFile)
$buffer = New-Object byte[] 10485760
$totalRead = 0
while ($true) {
    $bytesRead = $rstream.Read($buffer, 0, $buffer.Length)
    if ($bytesRead -eq 0) break
    $totalRead += $bytesRead
}
$rstream.Close()
$stopwatch.Stop()
$readMB = $totalRead / (1024*1024)
Write-Host "$([math]::Round($readMB,2))MB sequential read: $($stopwatch.ElapsedMilliseconds)ms"

# Cleanup
Remove-Item $testFile -Force
Write-Host ""
Write-Host "=== Done ==="
