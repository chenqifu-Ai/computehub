#!/bin/bash
# remote-upgrade.sh — 通过 Gateway Task 远程升级 Worker/Gateway（零 SSH）
# 原理：向 Gateway 提交 task → worker 领到任务 → 下载新二进制 → 替换 → 重启
#
# 用法:
#   bash scripts/remote-upgrade.sh                     # 默认: http://localhost:8282
#   bash scripts/remote-upgrade.sh <GATEWAY_URL>       # 指定 Gateway
#
# 示例:
#   bash scripts/remote-upgrade.sh http://36.250.122.43:8282

set -euo pipefail

GW="${1:-http://localhost:8282}"
VERSION=$(grep 'VERSION = "' "$(dirname "$0")/../src/version/version.go" | awk -F'"' '{print $2}')

echo "🔧 ComputeHub 远程升级 v${VERSION}"
echo "   Gateway: ${GW}"
echo "=============================================="
echo ""

# ── 1. 检查 Gateway 连通性 ──
echo "📡 检查 Gateway 连通性..."
HEALTH=$(curl -s --connect-timeout 5 "${GW}/api/health" 2>/dev/null)
if ! echo "$HEALTH" | grep -qi "healthy\|success"; then
  echo " ❌ Gateway 不可达: ${GW}"
  exit 1
fi
echo " ✅ Gateway 正常"

# ── 2. 列出当前节点 ──
echo ""
echo "📋 获取节点列表..."
NODES=$(curl -s --connect-timeout 5 "${GW}/api/v1/nodes" 2>/dev/null | python3 -c "
import json,sys
try:
    data = json.load(sys.stdin)
    nodes = data.get('data', data) if isinstance(data, dict) else data
    if isinstance(nodes, list):
        for n in nodes:
            nid = n.get('node_id','?')
            ip = n.get('ip_address','?')
            status = n.get('status','?')
            gpu = n.get('gpu_type','?')
            print(f'  {nid:30s} IP:{ip:15s} Status:{status:10s} GPU:{gpu}')
    else:
        print(json.dumps(nodes, indent=2)[:300])
except:
    print('  (解析失败)')
" 2>/dev/null || echo "  ⚠️ 无节点或接口不同")

echo "${NODES:-  (无节点)}"

# ── 3. 选择目标节点 ──
echo ""
read -r -p "🎯 输入要升级的节点 ID (直接回车升级所有在线节点): " TARGET_NODE
echo ""

# ── 4. 升级脚本（worker 执行的实际命令）──
UPGRADE_SCRIPT=$(cat <<'PYEOF'
import os, sys, json, urllib.request, hashlib, signal, time

GW = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8282"
NODE_ID = sys.argv[2] if len(sys.argv) > 2 else os.uname().nodename
VERSION = "0.7.10"

# 检测架构
import platform
arch_map = {"aarch64": "arm64", "arm64": "arm64", "x86_64": "amd64", "amd64": "amd64"}
arch = arch_map.get(platform.machine().lower(), "amd64")
binary_name = f"computehub-linux-{arch}"

print(f"[upgrade] Target: {NODE_ID} @ {arch}")

# 1. 从 Gallery 下载
gallery_url = f"{GW}/api/v1/gallery?format=json"
print(f"[upgrade] Fetching gallery: {gallery_url}")
try:
    req = urllib.request.Request(gallery_url)
    resp = urllib.request.urlopen(req, timeout=10)
    data = json.loads(resp.read())
    items = data.get("data", [])
    # 找最新的 computehub
    matching = [i for i in items if "computehub" in i["name"] and arch in i.get("path", "")]
    if not matching:
        # 回退：任何 computehub
        matching = [i for i in items if i["name"].startswith("computehub") and arch in i.get("name", "")]
    if not matching:
        matching = [i for i in items if i["name"].startswith("computehub")]
    
    if not matching:
        print(f"[upgrade] ❌ Gallery 中找不到 computehub ({arch})")
        sys.exit(1)
    
    # 选最新的（按 mod_time）
    matching.sort(key=lambda x: x.get("mod_time", ""), reverse=True)
    item = matching[0]
    dl_url = f"{GW}{item['url']}"
    dl_path = item["path"]
    print(f"[upgrade] 📦 最新: {item['name']} ({item.get('size_human','?')})")
except Exception as e:
    print(f"[upgrade] ❌ Gallery 查询失败: {e}")
    sys.exit(1)

# 2. 下载新二进制
tmp_path = f"/tmp/computehub-upgrade-{int(time.time())}"
print(f"[upgrade] ⬇️ 下载: {dl_url}")
try:
    urllib.request.urlretrieve(dl_url, tmp_path)
    size = os.path.getsize(tmp_path)
    print(f"[upgrade] ✅ 下载完成: {size/1024/1024:.1f}MB")
except Exception as e:
    print(f"[upgrade] ❌ 下载失败: {e}")
    sys.exit(1)

# 3. 替换二进制
current = "/usr/local/bin/computehub"
if os.path.exists("/data/data/com.termux/files/usr/bin"):
    current = "/data/data/com.termux/files/usr/bin/computehub"
elif not os.path.exists(current):
    # 找 ~/computehub
    home = os.path.expanduser("~/computehub")
    if os.path.exists(home):
        current = home

# 备份旧版本
if os.path.exists(current):
    backup = f"{current}.bak.{int(time.time())}"
    os.rename(current, backup)
    print(f"[upgrade] 💾 备份: {current} → {backup}")

os.rename(tmp_path, current)
os.chmod(current, 0o755)
print(f"[upgrade] ✅ 替换: {current}")

# 4. 验证新版本
ver = os.popen(f"{current} version 2>/dev/null").read().strip()
print(f"[upgrade] 📋 版本: {ver}")

# 5. 重启 worker 进程
print(f"[upgrade] 🔄 重启 worker...")
os.system("pkill -f 'computehub worker' 2>/dev/null || true")
os.system(f"nohup {current} worker --gw {GW} --node-id {NODE_ID} --interval 3 --concurrent 8 > /tmp/worker-upgrade.log 2>&1 &")
print(f"[upgrade] ✅ Worker 已重启 (PID: $(pgrep -f 'computehub worker' | head -1))")
print(f"[upgrade] ✅ 升级完成! v{VERSION}")
PYEOF

# ── 5. 创建升级任务 ──
UPGRADE_CMD="python3 -c 'import urllib.request, json; $(echo "$UPGRADE_SCRIPT" | python3 -c "import sys; print(sys.stdin.read().encode().decode('unicode_escape'))")' '${GW}' '${TARGET_NODE}'"

# 如果目标节点为空，给所有在线节点各发一个任务
if [ -z "$TARGET_NODE" ]; then
  echo "🔄 给所有在线节点创建升级任务..."
  ONLINE_NODES=$(curl -s "${GW}/api/v1/nodes" 2>/dev/null | python3 -c "
import json,sys
try:
    data = json.load(sys.stdin)
    nodes = data.get('data', data) if isinstance(data, dict) else data
    if isinstance(nodes, list):
        for n in nodes:
            if n.get('status','') in ('online','idle','busy'):
                print(n['node_id'])
except:
    pass
" 2>/dev/null)
  
  COUNT=0
  for NODE in $ONLINE_NODES; do
    TASK_ID="upgrade-${NODE}-$(date +%s)"
    COMMAND=$(cat <<PYEOF
python3 -c "
import urllib.request, json, os, sys, platform, time
GW='${GW}'
NODE='${NODE}'
# 检测架构
am = {'aarch64':'arm64','arm64':'arm64','x86_64':'amd64','amd64':'amd64'}
arch = am.get(platform.machine().lower(),'amd64')
# Gallery 查下载地址
data = json.loads(urllib.request.urlopen(urllib.request.Request(GW+'/api/v1/gallery?format=json'),timeout=10).read())['data']
items = [i for i in data if 'computehub' in i['name']]
items.sort(key=lambda x: x.get('mod_time',''), reverse=True)
url = GW + items[0]['url']
# 下载
tmp = '/tmp/ch-upgrade-'+str(int(time.time()))
urllib.request.urlretrieve(url, tmp)
# 替换
cur = '/usr/local/bin/computehub'
if os.path.exists('/data/data/com.termux/files/usr/bin'):
    cur = '/data/data/com.termux/files/usr/bin/computehub'
if os.path.exists(cur):
    os.rename(cur, cur+'.bak')
os.rename(tmp, cur); os.chmod(cur, 0o755)
print('✅ 升级完成, version='+os.popen(cur+' version').read().strip())
# 重启 worker
os.system('pkill -f computehub 2>/dev/null || true')
os.system(f'nohup {cur} worker --gw {GW} --node-id {NODE} --interval 3 --concurrent 8 > /tmp/worker.log 2>&1 &')
print('✅ Worker 已重启')
"
PYEOF
)
    RESP=$(curl -s -X POST "${GW}/api/v1/tasks/submit" \
      -H "Content-Type: application/json" \
      -d "$(python3 -c "
import json
print(json.dumps({
    'task_id': '${TASK_ID}',
    'node_id': '${NODE}',
    'command': '''${COMMAND}''',
    'timeout': 60
}))
")" 2>/dev/null)
    
    if echo "$RESP" | grep -q '"success":true'; then
      echo "   ✅ ${NODE} → 任务已提交 (${TASK_ID})"
      COUNT=$((COUNT + 1))
    else
      echo "   ❌ ${NODE} → 提交失败: $(echo $RESP | head -c 100)"
    fi
  done
  echo ""
  echo "=============================================="
  echo "📊 共提交 ${COUNT} 个升级任务"
  echo "   每个 Worker 会在下次轮询时认领并执行"
  echo "   查看状态: curl -s ${GW}/api/v1/tasks/list"
else
  # 单个节点升级
  TASK_ID="upgrade-${TARGET_NODE}-$(date +%s)"
  echo "🎯 向 ${TARGET_NODE} 提交升级任务..."
  
  RESP=$(curl -s -X POST "${GW}/api/v1/tasks/submit" \
    -H "Content-Type: application/json" \
    -d "$(python3 -c "
import json
print(json.dumps({
    'task_id': '${TASK_ID}',
    'node_id': '${TARGET_NODE}',
    'command': '${UPGRADE_CMD}',
    'timeout': 120
}))
")" 2>/dev/null)
  
  if echo "$RESP" | grep -q '"success":true'; then
    echo "   ✅ 任务已提交: ${TASK_ID}"
    echo "   查看: curl -s ${GW}/api/v1/tasks/list"
  else
    echo "   ❌ 提交失败: $(echo $RESP | head -c 200)"
  fi
fi

echo ""
echo "💡 查看所有节点升级状态:"
echo "   curl -s ${GW}/api/v1/tasks/list | python3 -m json.tool"
