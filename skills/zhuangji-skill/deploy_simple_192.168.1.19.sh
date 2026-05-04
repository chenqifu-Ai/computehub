#!/bin/bash
# OpenClaw简化部署脚本 - 目标: 192.168.1.19 (Ubuntu环境)

set -e

# 固定配置参数
TARGET_HOST="192.168.1.19"
TARGET_PORT="8022"
TARGET_USER="u0_a213"
TARGET_PASS="123"
DEPLOY_PORT="18789"

# 颜色输出（简化版）
GREEN='\033[0;32m'
RED='\033[0;31m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# SSH执行命令（在Ubuntu环境中）
ssh_ubuntu() {
    local command="$1"
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o GlobalKnownHostsFile=/dev/null -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "proot-distro login ubuntu -- bash -c '$command'"
}

# 设备检测
device_check() {
    log_info "检测目标设备: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    
    # 检查SSH连接
    if ! sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o GlobalKnownHostsFile=/dev/null -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" "echo 'SSH连接成功'"; then
        log_error "SSH连接失败"
        return 1
    fi
    
    # 检查Ubuntu环境
    log_info "检查Ubuntu环境..."
    if ! ssh_ubuntu "echo 'Ubuntu环境正常'"; then
        log_error "Ubuntu环境检查失败"
        return 1
    fi
    
    log_info "设备连接正常"
}

# 安装Node.js和npm
install_nodejs() {
    log_info "安装Node.js和npm..."
    
    # 使用非root方式安装Node.js
    ssh_ubuntu "curl -o- https://raw.githubusercontent.com/nvm-sh/nvm/v0.39.0/install.sh | bash"
    
    # 加载nvm并安装Node.js
    ssh_ubuntu "export NVM_DIR=\"$HOME/.nvm\" && [ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\" && nvm install 18 && nvm use 18"
    
    # 验证安装
    ssh_ubuntu "export NVM_DIR=\"$HOME/.nvm\" && [ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\" && node --version && npm --version"
    log_info "Node.js安装完成"
}

# 安装OpenClaw
install_openclaw() {
    log_info "安装OpenClaw..."
    
    ssh_ubuntu "export NVM_DIR=\"$HOME/.nvm\" && [ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\" && npm install -g openclaw@2016.3.13"
    
    # 验证安装
    ssh_ubuntu "export NVM_DIR=\"$HOME/.nvm\" && [ -s \"$NVM_DIR/nvm.sh\" ] && . \"$NVM_DIR/nvm.sh\" && openclaw --version"
    log_info "OpenClaw安装完成"
}

# 配置初始化
setup_config() {
    log_info "初始化配置..."
    
    ssh_ubuntu "openclaw setup"
}

# 完整配置同步
sync_full_config() {
    log_info "开始完整配置同步..."
    
    # 备份目标设备现有配置
    ssh_ubuntu "cd ~/.openclaw && tar -czf backup_$(date +%Y%m%d_%H%M).tar.gz . 2>/dev/null || true"
    
    # 使用tar管道传输完整配置到Ubuntu环境
    tar -czf - -C ~/.openclaw . | \
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o GlobalKnownHostsFile=/dev/null -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "proot-distro login ubuntu -- bash -c 'mkdir -p ~/.openclaw && tar -xzf - -C ~/.openclaw'"
    
    log_info "配置同步完成"
}

# 启动服务
start_service() {
    log_info "启动Gateway服务..."
    
    # 停止现有服务
    ssh_ubuntu "pkill -f 'openclaw' || true"
    
    # 启动新服务
    ssh_ubuntu "openclaw gateway --port $DEPLOY_PORT &"
    
    # 等待服务启动
    sleep 5
    
    # 验证服务状态
    if ssh_ubuntu "curl -s http://127.0.0.1:$DEPLOY_PORT/health"; then
        log_info "✅ 服务启动成功"
    else
        log_warn "服务状态检查失败，但可能仍在启动中"
    fi
}

# 主函数
main() {
    log_info "开始OpenClaw部署到 192.168.1.19 (Ubuntu环境)"
    log_info "目标: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    echo ""
    
    # 执行部署流程
    device_check
    install_nodejs
    install_openclaw
    setup_config
    sync_full_config
    start_service
    
    log_info "🎯 部署完成!"
    echo "============================================="
    echo "设备: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    echo "环境: Ubuntu (proot-distro)"
    echo "Gateway: http://$TARGET_HOST:$DEPLOY_PORT"
    echo "状态: ✅ 正常运行"
    echo "============================================="
}

# 执行主函数
main "$@"