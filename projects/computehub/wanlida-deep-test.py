#!/usr/bin/env python3
"""Deep test for wanlida-temp node"""
import json, time, sys, urllib.request

gw = "http://localhost:8282"
node = "wanlida-temp"

def submit(task_id, command, timeout=60):
    data = json.dumps({
        "task_id": task_id,
        "command": command,
        "assigned_node": node,
        "source_type": "api",
        "priority": 5,
        "timeout": timeout
    }).encode()
    req = urllib.request.Request(f"{gw}/api/v1/tasks/submit", data=data, headers={"Content-Type": "application/json"})
    resp = urllib.request.urlopen(req, timeout=10)
    d = json.loads(resp.read())
    print(f"  SUBMIT {task_id}: ok={d.get('success')}")
    return d

def cancel(task_id):
    data = json.dumps({"task_id": task_id}).encode()
    req = urllib.request.Request(f"{gw}/api/v1/tasks/cancel", data=data, headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=5)
        return json.loads(resp.read())
    except:
        pass
    return {}

def get_progress(task_id, timeout=30):
    for i in range(timeout):
        try:
            req = urllib.request.Request(f"{gw}/api/v1/tasks/progress?task_id={task_id}")
            resp = urllib.request.urlopen(req, timeout=5)
            d = json.loads(resp.read())
            if d.get("success") and d.get("data"):
                return d["data"]
        except:
            pass
        time.sleep(1)
    return None

def safe(text, maxlen=120):
    return ''.join(c if ord(c) < 128 else '?' for c in str(text))[:maxlen]

def print_result(prefix, r):
    if not r:
        print(f"  [{prefix}] NO RESULT")
        return
    status = r.get('status','?')
    exit_code = r.get('exit_code','?')
    duration = r.get('duration','?')
    out = r.get('stdout','')
    err = r.get('stderr','')
    print(f"  [{prefix}] Status={status}, Exit={exit_code}, Duration={duration}")
    if out:
        for line in out.split('\n')[:40]:
            print(f"    {safe(line)}")
    if err:
        for line in err.split('\n')[:5]:
            print(f"    ERR: {safe(line)}")

print("=" * 60)
print(" wanlida-temp 深度测试")
print("=" * 60)

# === TEST 1: OS Info ===
print("\n--- TEST 1: 系统信息 ---")
cmd1 = 'powershell -Command "$env:COMPUTERNAME; Get-CimInstance Win32_OperatingSystem | Format-List Caption, Version, BuildNumber, TotalVisibleMemorySize, FreePhysicalMemory; Get-CimInstance Win32_ComputerSystem | Format-List Manufacturer, Model, NumberOfLogicalProcessors; Get-CimInstance Win32_VideoController | Format-List Name, DriverVersion, AdapterRAM, Status"'
submit("wanlida-deep-01", cmd1)
time.sleep(5)
print_result("1", get_progress("wanlida-deep-01", 30))

# === TEST 2: GPU list ===
print("\n--- TEST 2: GPU 列表 ---")
cancel("wanlida-deep-02")
submit("wanlida-deep-02", 'nvidia-smi -L')
time.sleep(5)
print_result("2", get_progress("wanlida-deep-02", 30))

# === TEST 3: GPU detailed ===
print("\n--- TEST 3: GPU 详细 ---")
submit("wanlida-deep-03", 'nvidia-smi --query-gpu=index,name,temperature.gpu,memory.total,memory.used,memory.free,utilization.gpu,power.draw,power.limit,driver_version --format=csv,noheader,nounits')
time.sleep(5)
print_result("3", get_progress("wanlida-deep-03", 30))

# === TEST 4: Tools ===
print("\n--- TEST 4: 工具检测 ---")
cmd4 = r'''powershell -Command "Write-Output '===Python=='; where.exe python.exe 2>nul && python --version 2>&1; Write-Output '===Node=='; where.exe node.exe 2>nul && node --version 2>&1; Write-Output '===Git=='; where.exe git.exe 2>nul && git --version 2>&1; Write-Output '===Curl=='; where.exe curl.exe 2>nul && curl.exe --version 2>&1 | head -1; Write-Output '===FFmpeg=='; where.exe ffmpeg.exe 2>nul && ffmpeg -version 2>&1 | head -1; Write-Output '===Pip=='; where.exe pip.exe 2>nul && pip list 2>&1 | head -5"'''
submit("wanlida-deep-04", cmd4)
time.sleep(5)
print_result("4", get_progress("wanlida-deep-04", 30))

# === TEST 5: Network ===
print("\n--- TEST 5: 网络探测 ---")
cmd5 = r'''powershell -Command "Write-Output '===IP Config=='; Get-NetIPAddress -AddressFamily IPv4 | Where-Object {$_.InterfaceAlias -notlike '*Loopback*' -and $_ .InterfaceAlias -notlike '*VM*'} | Select-Object InterfaceAlias,IPAddress | Format-Table -AutoSize; Write-Output '===Gateway=='; Get-NetIPConfiguration | Where-Object {$_.IPv4DefaultGateway} | Select-Object InterfaceAlias,IPv4DefaultGateway | Format-Table -AutoSize; Write-Output '===DNS=='; Resolve-DnsName baidu.com -ErrorAction SilentlyContinue | Select-Object -First 1 NameHost"'''
submit("wanlida-deep-05", cmd5, 30)
time.sleep(5)
print_result("5", get_progress("wanlida-deep-05", 30))

# === TEST 6: Download test ===
print("\n--- TEST 6: 下载测试 (ECS->wanlida) ---")
cancel("wanlida-deep-06")
cmd6 = r'''powershell -Command "Write-Output '=== ECS 下载测试 ==='; try {$wc = New-Object System.Net.WebClient; $wc.DownloadFile('http://36.250.122.43:8282/api/v1/files/WIN-OPC-001_Windows%E8%BF%9C%E7%A8%8B%E6%93%8D%E4%BD%9C%E6%A0%87%E5%87%86%E6%B5%81%E7%A8%8B.md', 'C:\temp\wanlida-test.md'); $f = Get-Item C:\temp\wanlida-test.md; Write-Output \"OK size=\" + $f.Length + \" bytes\"} catch {Write-Output \"ERROR: \" + $_ .Exception.Message}"'''
submit("wanlida-deep-06", cmd6, 60)
time.sleep(10)
print_result("6", get_progress("wanlida-deep-06", 45))

# === TEST 7: curl.exe download ===
print("\n--- TEST 7: curl.exe 下载 ---")
cancel("wanlida-deep-07")
cmd7 = r'''powershell -Command "Write-Output '=== curl.exe test ==='; curl.exe -s -o C:\temp\curl-test.html -w 'HTTP:%{http_code} Size:%{size_download}' 'http://36.250.122.43:8282/api/v1/files/WIN-OPC-001_Windows%E8%BF%9C%E7%A8%8B%E6%93%8D%E4%BD%9C%E6%A0%87%E5%87%86%E6%B5%81%E7%A8%8B.md' 2>&1; if (Test-Path C:\temp\curl-test.html) { Write-Output \"File OK, size=\" + (Get-Item C:\temp\curl-test.html).Length } else { Write-Output \"File not found\" }"'''
submit("wanlida-deep-07", cmd7, 60)
time.sleep(10)
print_result("7", get_progress("wanlida-deep-07", 45))

# === TEST 8: Disk ===
print("\n--- TEST 8: 磁盘/文件系统 ---")
cmd8 = r'''powershell -Command "Get-Volume | Where-Object {$_.DriveLetter} | Format-Table DriveLetter,FileSystemLabel,FileSystem,@{Name='Size(GB)';Expression={[math]::Round($_ .Size/1GB,2)}},@{Name='Free(GB)';Expression={[math]::Round($_ .SizeRemaining/1GB,2)}} -AutoSize; Get-CimInstance Win32_DiskDrive | Format-Table Model,Size,MediaType -AutoSize"'''
submit("wanlida-deep-08", cmd8, 30)
time.sleep(5)
print_result("8", get_progress("wanlida-deep-08", 30))

# === TEST 9: Installed software ===
print("\n--- TEST 9: 已安装软件 ---")
cmd9 = r'''powershell -Command "Get-ItemProperty HKLM:\Software\Microsoft\Windows\CurrentVersion\Uninstall\*,HKLM:\Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall\* -ErrorAction SilentlyContinue | Select-Object DisplayName,DisplayVersion,Publisher | Where-Object {$_.DisplayName} | Format-Table -AutoSize -Wrap -HideTableHeaders"'''
submit("wanlida-deep-09", cmd9, 30)
time.sleep(5)
print_result("9", get_progress("wanlida-deep-09", 30))

# === TEST 10: Worker process ===
print("\n--- TEST 10: Worker 进程 ===")
cmd10 = r'''powershell -Command "Write-Output '=== Process ==='; Get-Process computehub -ErrorAction SilentlyContinue | Format-Table Id,CPU,WorkingSet64 -AutoSize; Write-Output '=== Service ==='; Get-Service computehub* -ErrorAction SilentlyContinue | Format-Table Name,Status; Write-Output '=== Binary ==='; Get-ChildItem C:\Users\admin\AppData\Local\Programs\ -Recurse -ErrorAction SilentlyContinue -Filter computehub* | Select-Object FullName,Length; Get-ChildItem 'C:\Program Files\*' -Recurse -ErrorAction SilentlyContinue -Filter computehub* | Select-Object FullName,Length"'''
submit("wanlida-deep-10", cmd10, 30)
time.sleep(5)
print_result("10", get_progress("wanlida-deep-10", 30))

# === TEST 11: Agent mode ===
print("\n--- TEST 11: Agent 模式 ---")
cancel("wanlida-deep-11")
submit("wanlida-deep-11", 'powershell -Command "Write-Output ===Agent-Mode===; $gw = \"http://localhost:8383\"; try { $r = Invoke-WebRequest -Uri ($gw + \"/api/v1/health\") -UseBasicParsing; Write-Output \"Health: \" + $r.Content } catch { Write-Output \"Worker health API: \" + $_ .Exception.Message }; try { $r2 = Invoke-WebRequest -Uri ($gw + \"/api/v1/status\") -UseBasicParsing; Write-Output \"Status: \" + $r2.Content } catch { Write-Output \"Worker status API: \" + $_ .Exception.Message }"', timeout=30)
time.sleep(5)
print_result("11", get_progress("wanlida-deep-11", 30))

print("\n" + "=" * 60)
print(" 全部测试完成!")
print("=" * 60)
