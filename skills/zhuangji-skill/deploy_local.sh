#!/bin/bash
# OpenClaw多设备部署脚本 - 本地资源版

set -e

# 配置参数
TARGET_HOST="$1"
TARGET_PORT="${2:-8022}"
TARGET_USER="${3:-u0_a213}"
TARGET_PASS="${4:-123}"
DEPLOY_PORT="${5:-18789}"
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

# 设备检测
device_check() {
    log_info "检测目标设备: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    
    # 检查SSH连接
    if ! sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" "echo 'SSH连接成功'"; then
        log_error "SSH连接失败"
        return 1
    fi
    
    # 检查系统信息
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "uname -a && echo '---' && free -h && echo '---' && df -h /data"
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
    
    # 检查本地npm缓存
    local NPM_CACHE="$HOME/.npm/_cacache/content-v2/sha512"
    
    # 检查已知包文件
    for package in "${LOCAL_PACKAGES[@]}"; do
        if [ -f "$package" ]; then
            log_info "找到本地安装包: $package"
            echo "$package"
            return 0
        fi
    done
    
    # 检查npm缓存
    if [ -d "$NPM_CACHE" ]; then
        local PACKAGE_FOUND=$(find "$NPM_CACHE" -name "*openclaw*" -type f | head -1)
        if [ -n "$PACKAGE_FOUND" ]; then
            log_info "找到npm缓存包: $PACKAGE_FOUND"
            echo "$PACKAGE_FOUND"
            return 0
        fi
    fi
    
    log_warn "未找到本地OpenClaw安装包"
    return 1
}

# 从本地安装OpenClaw
install_openclaw_local() {
    log_info "从本地资源安装OpenClaw $OPENCLAW_VERSION..."
    
    # 检查本地包
    local LOCAL_PACKAGE=$(check_local_package)
    
    if [ -n "$LOCAL_PACKAGE" ]; then
        # 使用本地包安装
        log_info "使用本地包安装: $LOCAL_PACKAGE"
        
        # 复制包到目标设备
        sshpass -p "$TARGET_PASS" scp -P "$TARGET_PORT" -o StrictHostKeyChecking=no \
            "$LOCAL_PACKAGE" "$TARGET_USER@$TARGET_HOST:/tmp/openclaw-package.tgz"
        
        # 在目标设备安装
        sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
            "npm install -g /tmp/openclaw-package.tgz && rm /tmp/openclaw-package.tgz"
    else
        # 回退到网络安装（但使用指定版本）
        log_warn "未找到本地包，使用网络安装指定版本"
        sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
            "npm install -g $OPENCLAW_VERSION"
    fi
    
    # 验证安装
    log_info "验证安装结果..."
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "openclaw --version && echo '✅ 安装成功!'"
}

# 配置初始化
setup_config() {
    log_info "初始化配置..."
    
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "openclaw setup"
}

# 完整配置同步
sync_full_config() {
    log_info "开始完整配置同步..."
    
    # 备份目标设备现有配置
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "cd ~/.openclaw && tar -czf backup_$(date +%Y%m%d_%H%M).tar.gz ."
    
    # 使用tar管道传输完整配置
    tar -czf - -C ~/.openclaw . | \
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "tar -xzf - -C ~/.openclaw"
    
    log_info "配置同步完成"
}

# 启动服务
start_service() {
    log_info "启动Gateway服务..."
    
    # 停止现有服务
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "pkill -f 'openclaw' || true"
    
    # 启动新服务
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "openclaw gateway --port $DEPLOY_PORT &"
    
    # 等待服务启动
    sleep 3
    
    # 验证服务状态
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "curl -s http://127.0.0.1:$DEPLOY_PORT/health"
}

# 功能验证
validate_deployment() {
    log_info "验证部署结果..."
    
    # 检查配置文件
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "ls -la ~/.openclaw/ | grep -E '(openclaw\.json|workspace|extensions)'"
    
    # 检查模型配置
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "grep -c 'apiKey' ~/.openclaw/openclaw.json"
    
    # 检查服务状态
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "netstat -tln | grep :$DEPLOY_PORT || curl -s http://127.0.0.1:$DEPLOY_PORT/health"
}

# 主函数
main() {
    log_info "开始OpenClaw多设备部署（本地资源版）"
    
    # 参数检查
    if [ -z "$TARGET_HOST" ]; then
        log_error "请指定目标主机"
        echo "用法: $0 <host> [port] [user] [password] [gateway-port]"
        exit 1
    fi
    
    # 执行部署流程
    device_check
    install_openclaw_local
    setup_config
    sync_full_config
    start_service
    validate_deployment
    
    log_info "🎯 部署完成!"
    echo "设备: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    echo "Gateway: http://$TARGET_HOST:$DEPLOY_PORT"
    echo "版本: $OPENCLAW_VERSION"
    echo "状态: ✅ 正常运行"
}

# 执行主函数
main "$@"