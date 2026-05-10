#!/bin/bash
# ComputeHub Gateway Ubuntu 部署脚本
# 用法: sudo ./deploy.sh

set -euo pipefail

DEPLOY_DIR="/opt/computehub"
VERSION="v0.7.1"

echo "======================================"
echo "ComputeHub Gateway 部署脚本 ${VERSION}"
echo "======================================"

# 检查 root 权限
if [ "$EUID" -ne 0 ]; then
    echo "❌ 请使用 sudo 运行此脚本"
    exit 1
fi

# 创建用户和目录
echo ""
echo "[1/6] 创建用户和目录..."
if ! id "compute" &>/dev/null; then
    useradd -r -s /bin/false compute
    echo "  ✅ 创建 compute 用户"
else
    echo "  ℹ️  compute 用户已存在"
fi

mkdir -p ${DEPLOY_DIR}/{bin,config,data,logs}
chown -R compute:compute ${DEPLOY_DIR}

# 复制二进制文件
echo ""
echo "[2/6] 复制二进制文件..."
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cp ${SCRIPT_DIR}/../bin/computehub-gateway ${DEPLOY_DIR}/bin/
cp ${SCRIPT_DIR}/../bin/computehub-worker ${DEPLOY_DIR}/bin/
chmod +x ${DEPLOY_DIR}/bin/*
echo "  ✅ 二进制文件已复制"

# 创建环境变量文件
echo ""
echo "[3/6] 创建环境变量..."
if [ ! -f ${DEPLOY_DIR}/config/.env ]; then
    cat > ${DEPLOY_DIR}/config/.env << ENV_EOF
# ComputeHub API Key (从阿里云控制台获取)
COMPUTEHUB_API_KEY="sk-65ca99f6fd55437fba47dc7ba7973242"
ENV_EOF
    chmod 600 ${DEPLOY_DIR}/config/.env
    chown compute:compute ${DEPLOY_DIR}/config/.env
    echo "  ✅ 创建 .env 文件（请修改 API Key）"
else
    echo "  ℹ️  .env 文件已存在"
fi

# 安装 systemd 服务
echo ""
echo "[4/6] 安装 systemd 服务..."
cp ../systemd/computehub-gateway.service /etc/systemd/system/
systemctl daemon-reload
echo "  ✅ 服务已安装"

# 创建日志目录
echo ""
echo "[5/6] 创建日志目录..."
mkdir -p ${DEPLOY_DIR}/logs
chown compute:compute ${DEPLOY_DIR}/logs
echo "  ✅ 日志目录已创建"

# 启动服务
echo ""
echo "[6/6] 启动服务..."
systemctl enable computehub-gateway
systemctl start computehub-gateway
sleep 3

# 检查服务状态
if systemctl is-active --quiet computehub-gateway; then
    echo ""
    echo "======================================"
    echo "✅ 部署成功！"
    echo "======================================"
    echo ""
    echo "服务状态: systemctl status computehub-gateway"
    echo "日志查看: journalctl -u computehub-gateway -f"
    echo "API 地址: http://localhost:8282"
    echo "健康检查: curl http://localhost:8282/api/health"
    echo ""
    echo "如需修改配置，编辑:"
    echo "  /opt/computehub/config/config.json"
    echo "  /opt/computehub/config/.env"
else
    echo ""
    echo "======================================"
    echo "❌ 服务启动失败！"
    echo "======================================"
    echo ""
    echo "查看日志: journalctl -u computehub-gateway -n 50"
    exit 1
fi
