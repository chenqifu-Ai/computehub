#!/bin/bash
# SSH 密钥管理脚本

set -e

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

# 生成 SSH 密钥
generate_ssh_key() {
    local key_type="${1:-ed25519}"
    local key_file="$HOME/.ssh/id_$key_type"
    local comment="openclaw-auto-access@$(hostname)"
    
    # 确保 SSH 目录存在
    mkdir -p "$HOME/.ssh"
    chmod 700 "$HOME/.ssh"
    
    if [ ! -f "$key_file" ]; then
        log_info "生成新的 $key_type 密钥..."
        ssh-keygen -t "$key_type" -f "$key_file" -N "" -C "$comment"
        log_info "密钥生成完成: $key_file"
    else
        log_info "密钥已存在: $key_file"
    fi
    
    # 显示密钥信息
    ssh-keygen -lf "${key_file}.pub"
}

# 同步密钥到目标设备
sync_keys_to_device() {
    local host="$1"
    local port="$2"
    local user="$3"
    local password="$4"
    local key_type="${5:-ed25519}"
    
    local key_file="$HOME/.ssh/id_$key_type"
    local pub_file="${key_file}.pub"
    
    if [ ! -f "$key_file" ]; then
        log_error "本地密钥文件不存在: $key_file"
        return 1
    fi
    
    log_info "同步密钥到设备: $user@$host:$port"
    
    # 确保目标设备 SSH 目录存在
    sshpass -p "$password" ssh -o StrictHostKeyChecking=no -p "$port" "$user@$host" \
        "mkdir -p ~/.ssh && chmod 700 ~/.ssh"
    
    # 同步密钥文件
    sshpass -p "$password" scp -P "$port" -o StrictHostKeyChecking=no \
        "$key_file" "$pub_file" \
        "$user@$host:~/.ssh/"
    
    # 设置正确的文件权限
    sshpass -p "$password" ssh -o StrictHostKeyChecking=no -p "$port" "$user@$host" \
        "chmod 600 ~/.ssh/id_$key_type && chmod 644 ~/.ssh/id_$key_type.pub"
    
    # 验证同步
    local remote_fingerprint=$(sshpass -p "$password" ssh -o StrictHostKeyChecking=no -p "$port" "$user@$host" \
        "ssh-keygen -lf ~/.ssh/id_$key_type.pub")
    
    local local_fingerprint=$(ssh-keygen -lf "$pub_file")
    
    if [ "$remote_fingerprint" = "$local_fingerprint" ]; then
        log_info "✅ 密钥同步成功 - 指纹: $(echo $local_fingerprint | awk '{print $2}')"
    else
        log_error "❌ 密钥同步验证失败"
        return 1
    fi
}

# 注册密钥到 GitHub
register_key_to_github() {
    local key_file="${1:-$HOME/.ssh/id_ed25519.pub}"
    local title="${2:-OpenClaw Auto Key}"
    
    if [ ! -f "$key_file" ]; then
        log_error "公钥文件不存在: $key_file"
        return 1
    fi
    
    local key_content=$(cat "$key_file")
    
    log_info "请手动将以下公钥添加到 GitHub:"
    echo "============================================="
    echo "标题: $title"
    echo "密钥:"
    echo "$key_content"
    echo "============================================="
    echo "访问: https://github.com/settings/keys"
    echo "点击 'New SSH key' 并粘贴上述内容"
}

# 测试 SSH 连接
test_ssh_connection() {
    local host="$1"
    local port="$2"
    local user="$3"
    local password="$4"
    
    log_info "测试 SSH 连接到: $user@$host:$port"
    
    if sshpass -p "$password" ssh -o StrictHostKeyChecking=no -p "$port" "$user@$host" "echo 'SSH连接成功'"; then
        log_info "✅ SSH 连接测试成功"
        return 0
    else
        log_error "❌ SSH 连接测试失败"
        return 1
    fi
}

# 主函数
main() {
    local action="${1:-help}"
    
    case "$action" in
        "generate")
            generate_ssh_key "$2"
            ;;
        "sync")
            if [ $# -lt 5 ]; then
                log_error "用法: $0 sync <host> <port> <user> <password> [key_type]"
                exit 1
            fi
            sync_keys_to_device "$2" "$3" "$4" "$5" "$6"
            ;;
        "github")
            register_key_to_github "$2" "$3"
            ;;
        "test")
            if [ $# -lt 5 ]; then
                log_error "用法: $0 test <host> <port> <user> <password>"
                exit 1
            fi
            test_ssh_connection "$2" "$3" "$4" "$5"
            ;;
        "help" | *)
            echo "SSH 密钥管理工具"
            echo "用法: $0 <command> [options]"
            echo ""
            echo "命令:"
            echo "  generate [key_type]   生成 SSH 密钥 (默认: ed25519)"
            echo "  sync <host> <port> <user> <pass> [key_type] 同步密钥到设备"
            echo "  github [key_file] [title]  显示 GitHub 注册指令"
            echo "  test <host> <port> <user> <pass> 测试 SSH 连接"
            echo "  help                   显示帮助信息"
            ;;
    esac
}

# 执行主函数
main "$@"