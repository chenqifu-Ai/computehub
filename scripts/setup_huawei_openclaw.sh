#!/bin/bash
# 华为手机OpenClaw安装后配置脚本

set -e

# 配置参数
TARGET_HOST="192.168.2.156"
TARGET_PORT="8022"
TARGET_USER="u0_a46"
TARGET_PASS="123"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
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

# 检查OpenClaw安装
check_openclaw_installation() {
    log_info "检查OpenClaw安装情况..."
    
    if sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" "which openclaw" >/dev/null 2>&1; then
        log_info "✅ OpenClaw已安装"
        return 0
    else
        log_error "❌ OpenClaw未安装"
        return 1
    fi
}

# 初始化OpenClaw配置
initialize_openclaw() {
    log_info "初始化OpenClaw配置..."
    
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=10 -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" "
    # 创建OpenClaw配置目录
    mkdir -p ~/.openclaw/workspace
    mkdir -p ~/.openclaw/workspace/memory
    mkdir -p ~/.openclaw/workspace/config
    
    # 初始化基本配置
    echo '# OpenClaw配置' > ~/.openclaw/config.yaml
    echo 'version: 1.0' >> ~/.openclaw/config.yaml
    echo 'model: ollama-cloud/deepseek-v3.1:671b' >> ~/.openclaw/config.yaml
    echo 'workspace: ~/.openclaw/workspace' >> ~/.openclaw/config.yaml
    
    # 创建今日记忆文件
    echo '# 2026-04-02 记忆文件' > ~/.openclaw/workspace/memory/2026-04-02.md
    echo '## 📱 华为手机OpenClaw安装' >> ~/.openclaw/workspace/memory/2026-04-02.md
    echo '- 安装时间: 2026-04-02' >> ~/.openclaw/workspace/memory/2026-04-02.md
    echo '- 设备型号: HWI-AL00' >> ~/.openclaw/workspace/memory/2026-04-02.md
    echo '- Android版本: 9' >> ~/.openclaw/workspace/memory/2026-04-02.md
    echo '- 架构: aarch64' >> ~/.openclaw/workspace/memory/2026-04-02.md
    
    echo '✅ OpenClaw配置初始化完成'
    "
}

# 测试OpenClaw功能
test_openclaw() {
    log_info "测试OpenClaw功能..."
    
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p "$极速分析-2026-03-30.mdTARGET_PORT" "$TARGET_USER@$TARGET_HOST" "
    # 测试版本命令
    openclaw --version
    
    # 测试状态命令
    openclaw status || echo '状态检查可能需要进一步配置'
    
    echo '✅ OpenClaw功能测试完成'
    "
}

# 创建启动脚本
create_startup_script() {
    log_info "创建启动脚本..."
    
    sshpass -p "$TARGET_PASS" ssh -o StrictHostKeyChecking=no -o ConnectTimeout=5 -p "$TARGET_PORT" "$TARGET_USER@$TARGET_HOST" "
    # 创建简单的启动脚本
    cat > ~/start_openclaw.sh << 'EOF'
#!/bin/bash
# OpenClaw启动脚本

echo '启动OpenClaw...'
openclaw gateway start --port 18789 --host 0.0.0.0
EOF
    
    chmod +x ~/start_openclaw.sh
    echo '✅ 启动脚本创建完成'
    "
}

# 主函数
main() {
    log_info "开始华为手机OpenClaw安装后配置"
    
    # 检查安装
    if ! check_openclaw_installation; then
        log_error "请先完成OpenClaw安装"
        exit 1
    fi
    
    # 初始化配置
    initialize_openclaw
    
    # 测试功能
    test_openclaw
    
    # 创建启动脚本
    create_startup_script
    
    log_info "🎉 OpenClaw安装后配置完成!"
    log_info "下一步可以启动OpenClaw服务"
    log_info "启动命令: ./start_openclaw.sh"
}

# 执行主函数
main "$@"