@echo off
chcp 65001 >nul
echo ComputeHub v1.3.0 自动升级
echo =============================
set GW=http://36.250.122.43:8282
set TMP=C:\computehub_new.exe

echo [1/3] Downloading...
curl -sLo %TMP% %GW%/api/v1/download?file=computehub.exe
if %ERRORLEVEL% NEQ 0 (
    echo Download failed!
    exit /b 1
)

echo [2/3] Waiting for Worker to exit...
:wait
tasklist /fi "IMAGENAME eq computehub.exe" 2>nul | find /i "computehub.exe" >nul
if errorlevel 1 goto replace
ping 127.0.0.1 -n 3 >nul
goto wait

:replace
echo [3/3] Replacing binary and starting...
copy /Y %TMP% C:\computehub.exe >nul
del %TMP%
start "" C:\computehub.exe worker --gw http://36.250.122.43:8282 --node-id Windows-mobile --interval 3 --concurrent 4 --heartbeat 10
echo Done.
del "%~f0"
