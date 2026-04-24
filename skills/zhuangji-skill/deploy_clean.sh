#!/bin/bash
# OpenClaw多设备部署脚本 - 清洁版

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
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \\
        "uname -a && echo '---' && free -h && echo '---' && df -h /data"
}

# OpenClaw安装
install_openclaw() {
    log_info "安装OpenClaw..."
    
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \\
        "npm install -g openclaw@latest"
    
    # 验证安装
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$极速USER@$TARGET_HOST" \\
        "openclaw --version"
}

# 配置初始化
setup_config() {
    log_info "初始化配置..."
    
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \\
        "openclaw setup"
}

# 完整配置同步
sync_full_config() {
    log_info "开始完整配置同步..."
    
    # 备份目标设备现有配置
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \\
        "cd ~/.openclaw && tar -czf backup_$(date +%Y%m%d_%H%M).tar.gz ."
    
    # 使用tar管道传输完整配置
    tar -czf - -C ~/.openclaw . | \\
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \\
        "tar -xzf - -C ~/.openclaw"
    
    log_info "配置同步完成"
}

# 启动服务
start_service() {
    log_info "启动Gateway服务..."
    
    # 停止现有服务
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \\
        "pkill -f 'openclaw' || true"
    
    # 启动新服务
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \\
        "openclaw gateway --port $DEPLOY_PORT &"
    
    # 等待服务启动
    sleep 3
    
    # 验证服务状态
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \\
        "curl -s http://127.0.0.1:$DEPLOY_PORT/health"
}

# 功能验证
validate_deployment() {
    log_info "验证部署结果..."
    
    # 检查配置文件
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -极速p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \\
        "ls -la ~/.openclaw/ | grep -E '(openclaw\\.json|workspace|extensions)'"
    
    # 检查模型配置
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \\
        "grep -c 'apiKey' ~/.openclaw/openclaw.json"
    
    # 检查服务状态
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \\
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
    start_service
    validate_deployment
    
    log_info "🎯 部署完成!"
    echo "设备: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    echo "Gateway: http://$TARGET_HOST:$DEPLOY_PORT"
    echo "状态: ✅ 正常运行"
}

# 执行主函数
main "$@"