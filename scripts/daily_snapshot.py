#!/usr/bin/env python3
"""每日系统快照 - 记录系统状态到 memory 日志"""
import subprocess, os, datetime

NOW = datetime.datetime.now(datetime.timezone(datetime.timedelta(hours=8)))
DATE = NOW.strftime("%Y-%m-%d")
MEM_DIR = "/root/.openclaw/workspace/memory"
os.makedirs(MEM_DIR, exist_ok=True)

def cmd(s):
    try:
        r = subprocess.run(s, shell=True, capture_output=True, text=True, timeout=15)
        return r.stdout.strip()
    except:
        return "(timeout)"

# 收集指标
load = cmd("cat /proc/loadavg | awk '{print $1, $2, $3}'")
mem = cmd("free -h | awk '/Mem:/{printf \"%s/%s (%s%%)\", $3, $2, $5}'")
disk = cmd("df -h / | awk 'NR==2{printf \"%s/%s (%s), %s available\", $3, $2, $5, $4}'")
uptime_str = cmd("uptime -p 2>/dev/null")
if not uptime_str:
    uptime_str = cmd("uptime")
git_log = cmd("cd /root/.openclaw/workspace && git log --oneline -1 2>/dev/null")

lines = [
    f"### 📸 每日系统快照 ({NOW.strftime('%H:%M')})",
    f"- **负载**: {load}",
    f"- **内存**: {mem}",
    f"- **磁盘**: {disk}",
    f"- **运行时间**: {uptime_str}",
    f"- **Git**: {git_log}",
    ""
]

today_file = os.path.join(MEM_DIR, f"{DATE}.md")
header = f"# 每日记录 - {DATE}\n\n"

if os.path.exists(today_file):
    with open(today_file, 'r') as f:
        existing = f.read()
    # Remove old header if present
    existing = existing.replace(header, "", 1)
    with open(today_file, 'w') as f:
        f.write(header + "\n".join(lines) + "\n\n" + existing)
else:
    with open(today_file, 'w') as f:
        f.write(header + "\n".join(lines) + "\n")

print(f"✅ 每日快照已写入 {today_file}")
for l in lines:
    print(l)
