#!/bin/bash
# 远程服务器内核更新脚本
# 执行方式: 在 36.250.122.43 上手动执行
# 前提: SSH 已恢复连接

echo "========================================="
echo "🔧 服务器内核更新"
echo "========================================="

# 1. 更新包列表
echo "[1/4] 更新软件包列表..."
sudo apt-get update -qq
echo "✅ 软件包列表已更新"

# 2. 安装内核更新
echo "[2/4] 安装内核更新..."
sudo apt-get install -y linux-image-generic linux-headers-generic linux-generic
echo "✅ 内核包已安装"

# 3. 确认版本
echo "[3/4] 确认内核版本..."
echo "当前内核: $(uname -r)"
dpkg -l | grep linux-image-generic | grep ^ii
echo ""

# 4. 检查是否需要重启
echo "[4/4] 重启检查..."
if [ -f /var/run/reboot-required ]; then
    cat /var/run/reboot-required
    echo ""
    echo "⚠️ 需要重启！"
else
    echo "✅ 无需重启"
fi

echo ""
echo "========================================="
echo "完成！如需重启请执行: sudo reboot"
echo "========================================="
