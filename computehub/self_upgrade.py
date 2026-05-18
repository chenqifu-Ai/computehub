#!/usr/bin/env python3
"""
ComputeHub 远程自升级
通过 Gateway task API 在 worker 上执行升级
用法: python3 self_upgrade.py [--binary-url URL]

默认从 GitHub Releases 下载
"""

import json
import sys
import time
import urllib.request
import urllib.error

GW = "http://localhost:8282"
NODE_ID = "ecs-p2ph"

# 升级用 Shell 脚本（在 Worker 上执行）
UPGRADE_SCRIPT = r"""
set -e
echo "[UPGRADE] 开始升级..."

# 1. 下载新二进制
URL="{binary_url}"
BIN="/home/computehub/computehub"
BACKUP="/home/computehub/computehub.bak.$(date +%s)"

echo "[UPGRADE] 下载: $URL"
curl -sL -o /tmp/computehub.new "$URL" --connect-timeout 30 --max-time 120

if [ ! -s /tmp/computehub.new ]; then
    echo "[UPGRADE] ❌ 下载失败"
    exit 1
fi

chmod +x /tmp/computehub.new
SIZE=$(stat -c%s /tmp/computehub.new)
echo "[UPGRADE] ✅ 下载完成: $(ls -lh /tmp/computehub.new | awk '{print $5}')"

# 2. 备份旧二进制
cp "$BIN" "$BACKUP"
echo "[UPGRADE] ✅ 备份旧二进制: $BACKUP"

# 3. 拷贝新二进制
cp /tmp/computehub.new "$BIN"
chmod +x "$BIN"
echo "[UPGRADE] ✅ 新二进制已部署"

# 4. 停旧进程
echo "[UPGRADE] 停止旧进程..."
pkill -f "computehub worker" 2>/dev/null || true
sleep 2
pkill -f "computehub gateway" 2>/dev/null || true
sleep 3

# 强制清理残留
if pgrep -f "computehub" > /dev/null 2>&1; then
    echo "[UPGRADE] ⚠️ 残留进程, 强制终止..."
    pkill -9 -f "computehub" 2>/dev/null || true
    sleep 2
fi

# 5. 启动新 Gateway
echo "[UPGRADE] 启动新 Gateway..."
cd /home/computehub
nohup ./computehub gateway --port 8282 > gateway.log 2>&1 &
GATEWAY_PID=$!
echo "[UPGRADE] Gateway PID: $GATEWAY_PID"

# 等待 Gateway 就绪
for i in 1 2 3 4 5 6 7 8 9 10; do
    if curl -sf --max-time 2 http://localhost:8282/api/v1/nodes >/dev/null 2>&1; then
        echo "[UPGRADE] ✅ Gateway 已就绪"
        break
    fi
    sleep 1
done

# 6. 启动新 Worker
echo "[UPGRADE] 启动新 Worker..."
nohup ./computehub worker --gw http://localhost:8282 \
    --node-id ecs-p2ph \
    --interval 3 \
    --concurrent 8 \
    --heartbeat 10 > worker.log 2>&1 &
WORKER_PID=$!
echo "[UPGRADE] Worker PID: $WORKER_PID"
sleep 3

# 7. 验证
echo "[UPGRADE] ===== 验证 ====="
ps aux | grep "computehub" | grep -v grep
echo "[UPGRADE] ================="
echo "[UPGRADE] ✅ 升级完成!"
"""


def submit_task(task_id, command, timeout=120):
    url = f"{GW}/api/v1/tasks/submit"
    body = json.dumps({
        "task_id": task_id,
        "command": command,
        "timeout": timeout
    }).encode()
    req = urllib.request.Request(url, data=body,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
            return data.get("success", False)
    except Exception as e:
        print(f"  ❌ 提交失败: {e}")
        return False


def get_task_detail(task_id):
    url = f"{GW}/api/v1/tasks/detail?task_id={task_id}&node_id={NODE_ID}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            d = data.get("data", {})
            return d.get("status"), d.get("success"), d.get("stdout", ""), d.get("stderr", "")
    except Exception as e:
        return "ERROR", False, "", str(e)


def main():
    binary_url = sys.argv[1] if len(sys.argv) > 1 else \
        "https://github.com/openclawlab/computehub/releases/download/v0.7.10/computehub-linux-arm64"

    print("=" * 60)
    print("  🚀 ComputeHub 远程自升级")
    print("=" * 60)
    print(f"  Gateway: {GW}")
    print(f"  Node:    {NODE_ID}")
    print(f"  Binary:  {binary_url}")
    print()

    # 1. 检查 Gateway
    print("🔍 检查节点状态...")
    try:
        resp = urllib.request.urlopen(f"{GW}/api/v1/nodes", timeout=5)
        nodes = json.loads(resp.read().decode())
        print(f"   ✅ Gateway 响应正常")
        print(f"   节点: {json.dumps(nodes, indent=2)[:200]}")
    except Exception as e:
        print(f"   ⚠️ 无法连接 Gateway: {e}")
        if input("继续? (y/N): ").lower() != "y":
            return

    print()

    # 2. 构建升级命令（注入 binary_url）
    cmd = UPGRADE_SCRIPT.format(binary_url=binary_url)

    # 3. 提交升级任务
    task_id = f"self-upgrade-{int(time.time())}"
    print(f"📤 提交升级任务: {task_id}")

    if not submit_task(task_id, cmd, timeout=180):
        print("❌ 任务提交失败")
        return

    print("   ✅ 任务已提交")
    print()

    # 4. 轮询结果
    print("👀 等待升级完成 (最长 180s)...")
    start = time.time()
    for i in range(60):
        time.sleep(3)
        status, success, stdout, stderr = get_task_detail(task_id)
        elapsed = time.time() - start

        if stdout:
            lines = [l for l in stdout.split("\n") if l.strip()]
            visible = [l for l in lines
                       if l.startswith("[UPGRADE]")]
            for l in visible[-3:]:
                print(f"   {l}")

        if status == "completed":
            print(f"\n✅ 升级完成! (耗时 {elapsed:.0f}s)")
            if success:
                print(f"   成功: {success}")
            # 打印关键日志
            for l in stdout.split("\n"):
                l = l.strip()
                if "[UPGRADE]" in l and ("✅" in l or "❌" in l or "====" in l):
                    print(f"   {l}")
            break
        elif status == "failed":
            print(f"\n❌ 升级失败 (耗时 {elapsed:.0f}s)")
            print(f"   stderr: {stderr[:500]}")
            break

        if elapsed > 180:
            print(f"\n⏰ 超时 (180s)")
            break

        if i % 5 == 0:
            print(f"   轮询中... ({elapsed:.0f}s / 状态: {status})")

    print()
    print("提示: 升级过程会重启 Gateway, 如果连接断开")
    print("等待 10 秒后重新连接即可")


if __name__ == "__main__":
    main()
