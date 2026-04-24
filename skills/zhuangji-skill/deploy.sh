#!/bin/bash
# OpenClaw多设备部署脚本

set -e

# 配置参数
TARGET_HOST="$1"
TARGET_PORT="${2:-8022}"
TARGET_USER="${3:-u0_a207}"
TARGET_PASS="${4:-123}"
DEPLOY_PORT="${5:-18789}"

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

# OpenClaw安装
install_openclaw() {
    log_info "安装OpenClaw..."
    
    # 显示版本选择界面
    echo "=============================================="
    echo "🔧 OpenClaw版本选择"
    echo "=============================================="
    echo "1. 最新稳定版 (openclaw@latest) - 推荐"
    echo "2. 测试版 (openclaw@beta)"
    echo "3. 开发版 (openclaw@dev)"
    echo "4. 指定版本 (手动输入)"
    echo "=============================================="
    
    # 交互式版本选择
    read -p "请选择版本 [1-4] (默认1): " VERSION_CHOICE
    VERSION_CHOICE="${VERSION_CHOICE:-1}"
    
    # 根据选择设置版本
    case "$VERSION_CHOICE" in
        "1")
            OPENCLAW_VERSION="openclaw@latest"
            log_info "选择: 最新稳定版"
            ;;
        "2")
            OPENCLAW_VERSION="openclaw@beta"
            log_warn "选择: 测试版 - 可能不稳定"
            ;;
        "3")
            OPENCLAW_VERSION="openclaw@dev"
            log_warn "选择: 开发版 - 仅供测试"
            ;;
        "4")
            read -p "请输入版本号 (如: openclaw@2026.4.2): " CUSTOM_VERSION
            OPENCLAW_VERSION="$CUSTOM_VERSION"
            log_info "选择: 自定义版本 $CUSTOM_VERSION"
            ;;
        *)
            OPENCLAW_VERSION="openclaw@latest"
            log_info "默认选择: 最新稳定版"
            ;;
    esac
    
    log_info "开始安装: $OPENCLAW_VERSION"
    
    # 安装选择的版本
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "npm install -g $OPENCLAW_VERSION"
    
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

# SSH 密钥同步
sync_ssh_keys() {
    log_info "开始 SSH 密钥同步..."
    
    # 确保本地 SSH 目录存在
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    
    # 检查本地密钥，如不存在则生成
    if [ ! -f "~/.ssh/id_ed25519" ]; then
        log_info "生成新的 ED25519 密钥..."
        ssh-keygen -t ed25519 -f ~/.ssh/id_ed25519 -N "" -C "openclaw-auto-access@$(hostname)"
    fi
    
    # 确保目标设备 SSH 目录存在
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "mkdir -p ~/.ssh && chmod 700 ~/.ssh"
    
    # 同步密钥文件到目标设备
    sshpass -p "$TARGET_PASS" scp -P "$TARGET_PORT" -o StrictHostKeyChecking=no \
        ~/.ssh/id_ed25519 ~/.ssh/id_ed25519.pub \
        "$TARGET_USER@$TARGET_HOST:~/.ssh/"
    
    # 设置正确的文件权限
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "chmod 600 ~/.ssh/id_ed25519 && chmod 644 ~/.ssh/id_ed25519.pub"
    
    # 显示密钥指纹
    local fingerprint=$(ssh-keygen -lf ~/.ssh/id_ed25519.pub | awk '{print $2}')
    log_info "SSH 密钥同步完成 - 指纹: $fingerprint"
}

# Git 环境配置
setup_git_environment() {
    log_info "配置 Git 环境..."
    
    # 设置全局 Git 配置
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "git config --global user.name 'OpenClaw User' && \
         git config --global user.email 'openclaw@example.com' && \
         git config --global core.sshCommand 'ssh -i ~/.ssh/id_ed25519'"
    
    log_info "Git 环境配置完成"
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
    
    # 检查 SSH 密钥配置
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "ls -la ~/.ssh/ && ssh-keygen -lf ~/.ssh/id_ed25519.pub"
    
    # 检查 Git 配置
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "git config --global --list | grep -E '(user\.name|user\.email|core\.sshCommand)'"
    
    # 检查服务状态
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "netstat -tln | grep :$DEPLOY_PORT || curl -s http://127.0.0.1:$DEPLOY_PORT/health"
}

# 主函数
main() {
    log_info "开始OpenClaw多设备部署"
    
    # 参数检查
    if [ -z "$TARGET_HOST" ]; then
        log_error "请指定目标主机"
        echo "用法: $0 <host> [port] [user] [password] [gateway-port]"
        exit 1
    fi
    
    # 执行部署流程
    device_check
    install_openclaw
    setup_config
    sync_full_config
    sync_ssh_keys
    setup_git_environment
    start_service
    validate_deployment
    
    log_info "🎯 部署完成!"
    echo "设备: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    echo "Gateway: http://$TARGET_HOST:$DEPLOY_PORT"
    echo "状态: ✅ 正常运行"
}

# 执行主函数
main "$@"