#!/bin/bash
# ============================================================
# upgrade.sh — 通过 Gateway Task 远程升级 Worker（零 SSH）
# 对齐 STD-CONFIG-001 v1.1
#
# 原理：提交 Task → Worker 认领 → 下载新 binary → 替换 → 重启
#
# 用法:
#   bash scripts/upgrade.sh                          # 升级全部（默认 localhost:8282）
#   bash scripts/upgrade.sh <GATEWAY_URL>             # 指定 Gateway
#   bash scripts/upgrade.sh <GATEWAY_URL> <NODE_ID>   # 升级单个节点
#
# 示例:
#   bash scripts/upgrade.sh http://36.250.122.43:8282
#   bash scripts/upgrade.sh http://36.250.122.43:8282 worker-ecs-p2ph
# ============================================================
set -euo pipefail

GW="${1:-http://localhost:8282}"
TARGET_NODE="${2:-}"
VERSION=$(grep 'VERSION = "' "$(dirname "$0")/../src/version/version.go" | awk -F'"' '{print $2}')

echo "🔧 ComputeHub 远程升级 v${VERSION}"
echo "   Gateway: ${GW}"
echo "=============================="

# ── 1. 检查 Gateway ──
HEALTH=$(curl -s --connect-timeout 5 "${GW}/api/health" 2>/dev/null)
if ! echo "$HEALTH" | grep -qi "healthy\|success"; then
  echo " ❌ Gateway 不可达: ${GW}"
  exit 1
fi
echo " ✅ Gateway 正常"

# ── 2. 获取节点列表 ──
NODES=$(curl -s --connect-timeout 5 "${GW}/api/v1/nodes" 2>/dev/null || echo "{}")
echo ""
echo "📋 节点列表:"
echo "$NODES" | python3 -c "
import json,sys
try:
    d = json.load(sys.stdin)
    nodes = d.get('data', d) if isinstance(d, dict) else d
    if not isinstance(nodes, list): nodes = []
    if not nodes: print('  (无在线节点)')
    for n in nodes:
        print(f\"  {n.get('node_id','?'):30s} {n.get('status','?'):10s} {n.get('gpu_type','CPU'):8s} {n.get('ip_address','?'):15s}\")
except: print('  (解析失败)')
" 2>/dev/null

# ── 3. 确认 ──
if [ -z "$TARGET_NODE" ]; then
  echo ""
  read -r -p "🎯 升级全部在线节点? [Y/n] " ans
  [[ "$ans" =~ ^[Nn] ]] && { echo "已取消"; exit 0; }
fi

# ── 4. Worker 执行的升级脚本 ──
# 以独立文件保存，通过 Python 三引号安全传递
UPGRADE_CODE=$(cat << 'PYEOF'
import os, sys, json, urllib.request, platform, time

GW = sys.argv[1]
NODE_ID = sys.argv[2]

arch_map = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64", "amd64": "amd64"}
arch = arch_map.get(platform.machine().lower(), "amd64")
print(f"[upgrade] {NODE_ID} @ {arch}")

# 1. 查 Gallery
req = urllib.request.Request(GW + "/api/v1/gallery?format=json")
resp = urllib.request.urlopen(req, timeout=10)
data = json.loads(resp.read())
items = [i for i in data.get("data", []) if "computehub" in i.get("name", "")]
items.sort(key=lambda x: x.get("mod_time", ""), reverse=True)
if not items:
    print("[upgrade] ❌ Gallery 中无 computehub")
    sys.exit(1)
item = items[0]
dl_url = GW + item["url"]
print(f"[upgrade] 📦 下载: {item['name']} ({item.get('size_human','?')})")

# 2. 下载
tmp = f"/tmp/ch-upgrade-{int(time.time())}"
urllib.request.urlretrieve(dl_url, tmp)
size = os.path.getsize(tmp) / 1024 / 1024
print(f"[upgrade] ✅ 下载完成 ({size:.1f} MB)")

# 3. 替换
current = "/usr/local/bin/computehub"
if os.path.exists("/data/data/com.termux/files/usr/bin"):
    current = "/data/data/com.termux/files/usr/bin/computehub"
elif not os.path.exists(current):
    home = os.path.expanduser("~/computehub")
    if os.path.exists(home):
        current = home
if os.path.exists(current):
    old_ver = os.popen(f"{current} version 2>/dev/null").read().strip()
    print(f"[upgrade] 💾 旧版本: {old_ver}")
    os.rename(current, f"{current}.bak.{int(time.time())}")
os.rename(tmp, current)
os.chmod(current, 0o755)

# 4. 验证
new_ver = os.popen(f"{current} version 2>/dev/null").read().strip()
print(f"[upgrade] 📋 新版本: {new_ver}")

# 5. 重启
print("[upgrade] 🔄 重启 Worker...")
os.system("pkill -f 'computehub worker' 2>/dev/null || true")
os.system(f"nohup {current} worker --gw {GW} --node-id {NODE_ID} --interval 3 --concurrent 8 > /tmp/worker-upgrade.log 2>&1 &")
print("[upgrade] ✅ 升级完成!")
PYEOF
)

# 编码成 base64 避免转义问题
UPGRADE_B64=$(echo "$UPGRADE_CODE" | base64 -w0)

# ── 5. 提交任务 ──
echo ""
echo "⏳ 提交升级任务..."

get_online_nodes() {
  echo "$NODES" | python3 -c "
import json,sys
try:
    d = json.load(sys.stdin)
    nodes = d.get('data', d) if isinstance(d, dict) else d
    if isinstance(nodes, list):
        for n in nodes:
            if n.get('status','') in ('online','idle','busy'):
                print(n['node_id'])
except: pass
" 2>/dev/null
}

submit_one() {
  local node="$1"
  local task_id="upgrade-${node}-$(date +%s)"

  # Worker 命令：base64 decode → 执行 Python
  local command="python3 << 'PYUPGRADE'
import base64, sys
exec(base64.b64decode('${UPGRADE_B64}').decode())
PYUPGRADE
${GW} ${node}"

  local payload
  payload=$(python3 -c "
import json
task = {
    'task_id': '${task_id}',
    'node_id': '${node}',
    'command': '''${command}''',
    'timeout': 120
}
print(json.dumps(task))
")

  local resp
  resp=$(curl -s -X POST "${GW}/api/v1/tasks/submit" \
    -H "Content-Type: application/json" \
    -d "$payload" 2>/dev/null)

  if echo "$resp" | grep -q '"success":true'; then
    echo "   ✅ ${node} → ${task_id}"
  else
    echo "   ❌ ${node} → $(echo "$resp" | head -c 80)"
  fi
}

# 使用更安全的方式：Python 直接构造 JSON
submit_one_safe() {
  local node="$1"
  local task_id="upgrade-${node}-$(date +%s)"

  python3 -c "
import json, subprocess, sys, os
node = '${node}'
task_id = '${task_id}'
gw = '${GW}'
upgrade_b64 = '${UPGRADE_B64}'

# 构建命令：base64 decode + python execute
command = f'''python3 -c \"import base64; exec(base64.b64decode(''' + upgrade_b64 + ''').decode())\" \"{gw}\" \"{node}\"'''
task = {
    'task_id': task_id,
    'node_id': node,
    'command': command,
    'timeout': 120
}
json_str = json.dumps(task)

# 直接 curl
cmd = ['curl', '-s', '-X', 'POST', f'{gw}/api/v1/tasks/submit',
       '-H', 'Content-Type: application/json',
       '-d', json_str]
result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
resp = result.stdout.strip()

if '\"success\":true' in resp:
    print(f'   ✅ {node} → {task_id}')
else:
    print(f'   ❌ {node} → {resp[:80]}')
" 2>/dev/null
}

COUNT=0
if [ -z "$TARGET_NODE" ]; then
  for node in $(get_online_nodes); do
    submit_one_safe "$node"
    COUNT=$((COUNT + 1))
  done
else
  submit_one_safe "$TARGET_NODE"
  COUNT=1
fi

echo ""
echo "=============================="
echo "📊 提交完成! ${COUNT} 个任务"
echo "   查看状态: curl -s ${GW}/api/v1/tasks/list"
echo "   观察 Worker 日志: watch tail -f /tmp/worker-upgrade.log"
