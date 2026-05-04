#!/bin/bash
# 系统安全加固脚本
# 目标：192.168.1.7

echo "=========================================="
echo "     系统安全加固脚本 v1.0"
echo "     目标: 192.168.1.7"
echo "     时间: $(date)"
echo "=========================================="
echo ""

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# 日志函数
log_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

log_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 检查是否为root
if [ "$EUID" -ne 0 ]; then 
    log_error "请使用root权限运行此脚本"
    exit 1
fi

# 步骤1: 检查并安装UFW
echo ""
echo "[步骤 1/6] 检查UFW防火墙..."
if command -v ufw &> /dev/null; then
    log_info "UFW已安装"
else
    log_warn "UFW未安装，正在安装..."
    apt-get update -qq && apt-get install -y -qq ufw
    log_info "UFW安装完成"
fi

# 步骤2: 重置并配置UFW
echo ""
echo "[步骤 2/6] 配置UFW默认策略..."
ufw --force reset &> /dev/null
ufw default deny incoming
ufw default allow outgoing
log_info "默认策略: 拒绝入站，允许出站"

# 步骤3: 允许必要端口
echo ""
echo "[步骤 3/6] 配置允许的端口..."
ufw allow 22/tcp comment 'SSH'
log_info "允许端口 22 (SSH)"

# 限制Ollama API访问（只允许内网）
ufw allow from 192.168.1.0/24 to any port 11434 comment 'Ollama API (LAN only)'
log_info "允许端口 11434 (Ollama API, 仅限内网)"

# 步骤4: 拒绝高危端口
echo ""
echo "[步骤 4/6] 关闭高危端口..."
ufw deny 135/tcp comment 'MSRPC - 高危'
ufw deny 139/tcp comment 'NetBIOS - 高危'
ufw deny 445/tcp comment 'SMB - 高危'
log_info "已关闭端口 135, 139, 445 (SMB服务)"

# 步骤5: 启用防火墙
echo ""
echo "[步骤 5/6] 启用UFW防火墙..."
echo "y" | ufw enable
log_info "UFW防火墙已启用"

# 步骤6: 验证配置
echo ""
echo "[步骤 6/6] 验证防火墙配置..."
ufw status verbose

echo ""
echo "=========================================="
echo "     安全加固完成!"
echo "=========================================="
echo ""
echo "配置摘要:"
echo "  ✅ SSH (22) - 允许"
echo "  ✅ Ollama API (11434) - 仅内网"
echo "  ❌ MSRPC (135) - 已阻止"
echo "  ❌ NetBIOS (139) - 已阻止"
echo "  ❌ SMB (445) - 已阻止"
echo ""
echo "如需添加其他规则，使用: ufw allow [端口]/[协议]"
echo "查看状态: ufw status verbose"
echo "日志文件: /var/log/ufw.log"
echo ""

# 记录操作日志
echo "[$(date)] 安全加固执行完成" >> /var/log/security-hardening.log
