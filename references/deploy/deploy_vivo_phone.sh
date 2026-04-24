#!/bin/bash
# OpenClaw vivo手机专用部署脚本

set -e

# 配置参数 - 针对vivo手机定制
TARGET_HOST="192.168.2.93"
TARGET_PORT="8022"
TARGET_USER="u0_a355"
TARGET_PASS="123"
DEPLOY_PORT="18789"

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

# OpenClaw更新
update_openclaw() {
    log_info "更新OpenClaw到最新版本..."
    
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "npm update -g openclaw"
    
    # 验证版本
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "openclaw --version"
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

# 重启服务
restart_service() {
    log_info "重启Gateway服务..."
    
    # 停止现有服务
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "pkill -f 'openclaw' || true"
    
    # 等待进程结束
    sleep 2
    
    # 启动新服务
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "openclaw gateway --port $DEPLOY_PORT &"
    
    # 等待服务启动
    sleep 5
    
    # 验证服务状态
    if sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "curl -s http://127.0.0.1:$DEPLOY_PORT/health"; then
        log_info "✅ Gateway服务启动成功"
    else
        log_error "❌ Gateway服务启动失败"
        return 1
    fi
}

# 功能验证
validate_deployment() {
    log_info "验证部署结果..."
    
    # 检查配置文件
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "ls -la ~/.openclaw/ | head -10"
    
    # 检查版本
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" \
        "openclaw --version"
    
    # 检查服务状态
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -p "$TARGET_PORT" "$极速USER@$TARGET_HOST" \
        "ps aux | grep openclaw | grep -v grep"
}

# 主函数
main() {
    log_info "开始vivo手机OpenClaw部署更新"
    log_info "目标设备: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    
    # 执行部署流程
    device_check
    update_openclaw
    sync_full_config
    restart_service
    validate_deployment
    
    log_info "🎯 vivo手机OpenClaw部署完成!"
    echo "设备: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    echo "Gateway: http://$TARGET_HOST:$DEPLOY_PORT"
    echo "状态: ✅ 正常运行"
}

# 执行主函数
main "$@"