#!/bin/bash
# ============================================================
# ComputeHub v0.7.9 部署脚本 (ubuntu-01: 36.250.122.43)
# 修复: Gallery 删除 API + 视频脚本路径 + Gateway 恢复
# ============================================================
set -e

echo "========================================"
echo "🚀 ComputeHub v0.7.9 部署开始"
echo "========================================"

# --- 1. 备份旧版本 ---
echo ""
echo "[1/5] 备份旧版本..."
BACKUP_DIR="/var/computehub/backup/$(date +%Y%m%d_%H%M%S)"
mkdir -p "$BACKUP_DIR"

# 停止旧进程
echo "  停止旧 Gateway..."
pkill -f "computehub.*gateway" 2>/dev/null || true
sleep 2

# 备份二进制
if [ -f /usr/local/bin/computehub ]; then
    cp /usr/local/bin/computehub "$BACKUP_DIR/"
    echo "  ✅ 已备份 /usr/local/bin/computehub → $BACKUP_DIR/"
fi

# 备份 Gallery 文件
if [ -d /home/computehub/gallery ]; then
    tar czf "$BACKUP_DIR/gallery-backup.tar.gz" -C /home/computehub gallery/
    echo "  ✅ 已备份 Gallery 文件"
fi

# 备份配置
if [ -f /home/computehub/config.json ]; then
    cp /home/computehub/config.json "$BACKUP_DIR/"
    echo "  ✅ 已备份 config.json"
fi

# --- 2. 部署新二进制 ---
echo ""
echo "[2/5] 部署新二进制..."
# 将 computehub-v0.7.9 上传到这里再执行
# 如果脚本在服务器上直接运行，请确保 /tmp/computehub-v0.7.9 存在
BINARY_PATH="/tmp/computehub-v0.7.9"

if [ ! -f "$BINARY_PATH" ]; then
    echo "  ⚠️  二进制文件不存在: $BINARY_PATH"
    echo "  请通过 scp 上传:"
    echo "  scp /tmp/computehub-v0.7.9 computehub@36.250.122.43:/tmp/"
    exit 1
fi

cp "$BINARY_PATH" /usr/local/bin/computehub
chmod +x /usr/local/bin/computehub
echo "  ✅ 二进制已部署到 /usr/local/bin/computehub"

# --- 3. 部署视频脚本 ---
echo ""
echo "[3/5] 部署视频脚本..."
SCRIPTS_PATH="/tmp/computehub-scripts.tar.gz"

if [ ! -f "$SCRIPTS_PATH" ]; then
    echo "  ⚠️  脚本包不存在: $SCRIPTS_PATH"
    echo "  请通过 scp 上传:"
    echo "  scp /tmp/computehub-scripts.tar.gz computehub@36.250.122.43:/tmp/"
    echo "  跳过视频脚本部署"
else
    mkdir -p /home/computehub/scripts
    tar xzf "$SCRIPTS_PATH" -C /home/computehub/scripts/
    echo "  ✅ 视频脚本已部署到 /home/computehub/scripts/video/"
    ls -la /home/computehub/scripts/video/
fi

# --- 4. 确保必要目录 ---
echo ""
echo "[4/5] 创建必要目录..."
mkdir -p /home/computehub/gallery
mkdir -p /home/computehub/config
mkdir -p /var/computehub/gallery
mkdir -p /tmp/computehub-video/progress
echo "  ✅ 目录创建完成"

# --- 5. 启动 Gateway ---
echo ""
echo "[5/5] 启动 Gateway..."
cd /home/computehub

# 检查 config.json
if [ ! -f /home/computehub/config.json ]; then
    echo "  ⚠️  config.json 不存在，使用默认配置"
    cat > /home/computehub/config.json << 'EOFCONFIG'
{
  "gateway_port": 8282,
  "gateway_host": "0.0.0.0",
  "dashboard_dir": "",
  "gallery_root": "/home/computehub/gallery",
  "node_register_timeout": 30,
  "heartbeat_interval": 10,
  "max_workers": 100,
  "task_timeout": 300,
  "prometheus_enabled": true
}
EOFCONFIG
    echo "  ✅ 已创建默认 config.json"
fi

# 使用 nohup 启动（守护进程）
nohup /usr/local/bin/computehub gateway --port 8282 --config /home/computehub/config.json \
    > /tmp/computehub-gateway.log 2>&1 &
GATEWAY_PID=$!

sleep 3

# 验证启动
if kill -0 $GATEWAY_PID 2>/dev/null; then
    echo "  ✅ Gateway 已启动 (PID: $GATEWAY_PID)"
else
    echo "  ❌ Gateway 启动失败！"
    echo "  查看日志: cat /tmp/computehub-gateway.log"
    exit 1
fi

# --- 验证 ---
echo ""
echo "========================================"
echo "🎉 v0.7.9 部署完成!"
echo "========================================"
echo ""
echo "📊 验证命令:"
echo "  # 健康检查"
echo "  curl http://localhost:8282/api/health"
echo ""
echo "  # 系统状态"
echo "  curl http://localhost:8282/api/status"
echo ""
echo "  # 节点列表"
echo "  curl http://localhost:8282/api/v1/nodes/list"
echo ""
echo "  # Gallery 页面"
echo "  curl -s -o /dev/null -w '%{http_code}' http://localhost:8282/"
echo ""
echo "  # 测试删除 API (JSON body)"
echo "  curl -s -X POST http://localhost:8282/api/v1/gallery/delete \\"
echo "    -H 'Content-Type: application/json' \\"
echo "    -d '{\"name\":\"test.bin\"}'"
echo ""
echo "⏰ 日志: tail -f /tmp/computehub-gateway.log"
echo ""
