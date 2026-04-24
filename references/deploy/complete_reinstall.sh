#!/bin/bash
# OpenClaw完全重装脚本

set -e

# 配置参数
TARGET_HOST="10.35.204.26"
TARGET_PORT="8022"
TARGET_USER="u0_a46"
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

# 稳定的SSH执行函数
ssh_exec() {
    local cmd="$1"
    local max_retries=3
    local retry_delay=2
    
    for attempt in $(seq 1 $max_retries); do
        if sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" "$cmd" 2>/dev/null; then
            return 0
        else
            echo "尝试 $attempt/$max_retries 失败，等待 ${retry_delay}秒后重试..."
            sleep $retry_delay
        fi
    done
    
    return 1
}

# 1. 清理环境
clean_environment() {
    log_info "步骤1: 清理环境"
    
    # 杀死相关进程
    ssh_exec "pkill -f 'openclaw' || true" 
    ssh_exec "pkill -f 'node' || true"
    
    # 删除配置目录
    ssh_exec "rm -rf ~/.openclaw/ 2>/dev/null || true"
    ssh_exec "rm -rf ~/.npm/_cacache/ 2>/dev/null || true"
    
    log_info "环境清理完成"
}

# 2. 安装OpenClaw
install_openclaw() {
    log_info "步骤2: 安装OpenClaw"
    
    # 清理npm缓存
    ssh_exec "npm cache clean --force 2>/dev/null || true"
    
    # 安装最新版本
    if ssh_exec "npm install -g openclaw@latest"; then
        log_info "OpenClaw安装成功"
        return 0
    else
        log_error "OpenClaw安装失败"
        return 1
    fi
}

# 3. 基础配置
setup_config() {
    log_info "步骤3: 基础配置"
    
    # 创建基础配置
    ssh_exec "openclaw setup 2>/dev/null" || {
        log_warn "Setup失败，手动创建配置目录"
        ssh_exec "mkdir -p ~/.openclaw/"
    }
    
    log_info "基础配置完成"
}

# 4. 配置优化
optimize_config() {
    log_info "步骤4: 配置优化"
    
    # 设置允许Host头回退
    ssh_exec "openclaw config set gateway.controlUi.dangerouslyAllowHostHeaderOriginFallback true"
    
    # 设置LAN绑定
    ssh_exec "openclaw config set gateway.bind lan"
    
    log_info "配置优化完成"
}

# 5. 启动服务
start_service() {
    log_info "步骤5: 启动Gateway服务"
    
    # 启动服务
    ssh_exec "nohup openclaw gateway --port $DEPLOY_PORT > ~/gateway.log 2>> ~/gateway.log </dev/null &"
    
    # 等待启动
    sleep 5
    
    # 检查服务状态
    if ssh_exec "curl -s http://127.0.0.1:$DEPLOY_PORT/health 2>/dev/null"; then
        log_info "Gateway服务启动成功"
        return 0
    else
        log_warn "Gateway服务启动检查失败，查看日志..."
        ssh_exec "tail -10 ~/gateway.log 2>/dev/null || echo '无日志'"
        return 1
    fi
}

# 6. 验证部署
verify_deployment() {
    log_info "步骤6: 验证部署"
    
    # 检查版本
    ssh_exec "openclaw --version"
    
    # 检查配置
    ssh_exec "ls -la ~/.openclaw/ 2>/dev/null | head -3"
    
    # 检查端口
    ssh_exec "netstat -tln 2>/dev/null | grep :$DEPLOY_PORT || echo '端口检查失败'"
    
    log_info "部署验证完成"
}

# 主函数
main() {
    log_info "开始OpenClaw完全重装部署"
    log_info "目标设备: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    
    # 检查网络连通性
    if ! ping -c 1 -W 2 "$TARGET_HOST" >/dev/null 2>&1; then
        log_error "设备网络不可达"
        return 1
    fi
    
    # 执行部署流程
    clean_environment
    install_openclaw
    setup_config
    optimize_config
    start_service
    verify_deployment
    
    log_info "🎯 部署完成!"
    echo "设备: $TARGET_USER@$TARGET_HOST:$TARGET_PORT"
    echo "Gateway: http://$TARGET_HOST:$DEPLOY_PORT"
    echo "状态: ✅ 重新安装完成"
    
    return 0
}

# 执行主函数
main "$@"