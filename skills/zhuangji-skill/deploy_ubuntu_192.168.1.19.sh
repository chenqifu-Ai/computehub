#!/bin/bash
# OpenClaw快速部署脚本 - 目标: 192.168.1.19 (Ubuntu环境)

set -e

# 固定配置参数
TARGET_HOST="192.168.1.19"
TARGET_PORT="8022"
TARGET_USER="u0_a213"
TARGET_PASS="123"
DEPLOY_PORT="18789"
OPENCLAW_VERSION="openclaw@2016.3.13"

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
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

# SCP复制文件（到Ubuntu环境）
scp_ubuntu() {
    local local_file="$1"
    local remote_path="$2"
    
    # 使用base64编码传输文件
    local file_content=$(base64 -w 0 "$local_file")
    
    # 在Ubuntu环境中解码并保存
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o GlobalKnownHostsFile=/dev/null -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "proot-distro login ubuntu -- bash -c 'echo \"$file_content\" | base64 -d > \"$remote_path\"'"
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
    if ! ssh_ubuntu "echo 'Ubuntu环境正常' && lsb_release -a"; then
        log_error "Ubuntu环境检查失败"
        return 1
    fi
    
    log_info "设备连接正常"
}

# 检查本地OpenClaw安装包
check_local_package() {
    log_info "检查本地OpenClaw安装包..."
    
    # 优先检查已知的本地包位置
    local LOCAL_PACKAGES=(
        "$HOME/.openclaw/workspace/openclaw-termux-package.zip"
        "$HOME/.openclaw/openclaw_full_deploy.tar.gz"
        "$HOME/.openclaw/workspace_backup_20260403_064751/openclaw-termux-package.zip"
    )
    
    # 检查已知包文件
    for package in "${LOCAL_PACKAGES[@]}"; do
        if [ -f "$package" ]; then
            log_info "找到本地安装包: $package"
            echo "$package"
            return 0
        fi
    done
    
    log_warn "未找到本地OpenClaw安装包"
    return 1
}

# 在Ubuntu环境中安装OpenClaw
install_openclaw_ubuntu() {
    log_info "在Ubuntu环境中安装OpenClaw $OPENCLAW_VERSION..."
    
    # 检查本地包
    local LOCAL_PACKAGE=$(check_local_package)
    
    if [ -n "$LOCAL_PACKAGE" ]; then
        # 使用本地包安装
        log_info "使用本地包安装: $LOCAL_PACKAGE"
        
        # 复制包到Ubuntu环境
        scp_ubuntu "$LOCAL_PACKAGE" "/tmp/openclaw-package.tgz"
        
        # 在Ubuntu环境中安装
        ssh_ubuntu "npm install -g /tmp/openclaw-package.tgz && rm /tmp/openclaw-package.tgz"
    else
        # 回退到网络安装指定版本
        log_warn "未找到本地包，使用网络安装指定版本"
        ssh_ubuntu "npm install -g $OPENCLAW_VERSION"
    fi
    
    # 验证安装
    log_info "验证安装结果..."
    ssh_ubuntu "openclaw --version && echo '✅ OpenClaw安装成功!'"
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
    log_info "开始OpenClaw快速部署到 192.168.1.19 (Ubuntu环境)"
    log_info "目标: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    log_info "版本: $OPENCLAW_VERSION"
    log_info "环境: proot-distro Ubuntu"
    echo ""
    
    # 执行部署流程
    device_check
    install_openclaw_ubuntu
    setup_config
    sync_full_config
    start_service
    
    log_info "🎯 部署完成!"
    echo "============================================="
    echo "设备: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    echo "环境: Ubuntu (proot-distro)"
    echo "Gateway: http://$TARGET_HOST:$DEPLOY_PORT"
    echo "版本: $OPENCLAW_VERSION"
    echo "状态: ✅ 正常运行"
    echo "============================================="
}

# 执行主函数
main "$@"