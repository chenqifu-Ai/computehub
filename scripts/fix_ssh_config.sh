#!/bin/bash
# 修复SSH配置和部署公钥

echo "🔧 修复SSH配置..."

# 1. 确保本地SSH配置正确
cat > ~/.ssh/config << 'EOF'
# OpenClaw自动化访问配置
Host mi-pad
    HostName 192.168.1.19
    Port 8022
    User u0_a207
    IdentityFile ~/.ssh/id_openclaw
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts_mi_pad

Host mi-pad-backup
    HostName 192.168.1.19
    Port 8022  
    User u0_a46
    IdentityFile ~/.ssh/id_openclaw
    StrictHostKeyChecking no
    UserKnownHostsFile ~/.ssh/known_hosts_mi_pad
EOF

echo "✅ 本地SSH配置更新完成"

# 2. 检查并安装必要工具
echo "检查必要工具..."
if ! command -v sshpass >/dev/null 2>&1; then
    echo "安装sshpass..."
    apt update && apt install -y sshpass
fi

if ! command -v expect >/dev/null 2>&1; then
    echo "安装expect..."
    apt update && apt install -y expect
fi

# 3. 创建智能部署脚本
cat > /root/deploy_ssh_key_intelligent.sh << 'EOF'
#!/bin/bash
# 智能SSH公钥部署脚本

HOST="192.168.1.19"
PORT="8022"

# 尝试自动发现用户名
 discover_username() {
    echo "🔍 尝试发现正确的用户名..."
    
    # 常见用户名列表
    local users=("u0_a207" "u0_a46" "root" "admin" "termux" "user")
    
    for user in "${users[@]}"; do
        echo -n "测试用户名: $user..."
        
        # 测试连接（不要求密码）
        if timeout 3 ssh -o BatchMode=yes -o ConnectTimeout=2 -p $PORT $user@$HOST "echo found" 2>/dev/null; then
            echo " ✅ 发现!"
            echo "$user"
            return 0
        else
            echo " ❌"
        fi
    done
    
    echo "❌ 无法自动发现用户名"
    return 1
}

# 主函数
main() {
    echo "🚀 智能SSH公钥部署"
    echo "===================="
    
    # 获取公钥
    PUBLIC_KEY=$(cat ~/.ssh/id_openclaw.pub)
    if [ -z "$PUBLIC_KEY" ]; then
        echo "❌ 未找到公钥文件"
        exit 1
    fi
    
    echo "📋 公钥: ${PUBLIC_KEY:0:50}..."
    
    # 尝试发现用户名
    USERNAME=$(discover_username)
    if [ $? -ne 0 ]; then
        echo "💡 请手动输入用户名: "
        read -r USERNAME
    fi
    
    echo "🔑 使用用户名: $USERNAME"
    echo "💡 请输入密码: "
    read -rs PASSWORD
    echo
    
    # 使用expect部署公钥
    echo "部署公钥到 $USERNAME@$HOST:$PORT..."
    
    /usr/bin/expect <<EOF
set timeout 10
spawn ssh -p $PORT $USERNAME@$HOST

expect {
    "*password:" {
        send "$PASSWORD\r"
        exp_continue
    }
    "*$ " {
        send "mkdir -p ~/.ssh \u0026\u0026 chmod 700 ~/.ssh\r"
        expect "*$ "
        
        send "echo '$PUBLIC_KEY' \u003e\u003e ~/.ssh/authorized_keys\r"
        expect "*$ "
        
        send "chmod 600 ~/.ssh/authorized_keys\r"
        expect "*$ "
        
        send "echo '✅ SSH公钥部署完成'\r"
        expect "*$ "
        
        send "exit\r"
        expect eof
    }
    "*Permission denied*" {
        puts "\n❌ 权限被拒绝，请检查密码"
        exit 1
    }
    timeout {
        puts "\n❌ 连接超时"
        exit 1
    }
}
EOF

    if [ $? -eq 0 ]; then
        echo "✅ 公钥部署成功!"
        
        # 测试无密码连接
        echo "测试无密码连接..."
        ssh -p $PORT $USERNAME@$HOST "echo '🎉 无密码连接成功!'"
        
        if [ $? -eq 0 ]; then
            echo "🎊 SSH密钥认证配置完成!"
            
            # 更新SSH配置
            sed -i "s/User.*/User $USERNAME/" ~/.ssh/config
            echo "✅ SSH配置已更新: User = $USERNAME"
        else
            echo "⚠️  无密码连接测试失败"
        fi
    else
        echo "❌ 公钥部署失败"
        exit 1
    fi
}

main "$@"
EOF

chmod +x /root/deploy_ssh_key_intelligent.sh

echo "✅ 智能部署脚本创建完成: /root/deploy_ssh_key_intelligent.sh"

# 4. 创建使用说明
echo ""
echo "🚀 使用说明:"
echo "============"
echo "1. 运行智能部署脚本:"
echo "   bash /root/deploy_ssh_key_intelligent.sh"
echo ""
echo "2. 脚本会:"
echo "   • 自动尝试发现用户名"
echo "   • 提示输入密码"  
echo "   • 部署公钥到远程服务器"
echo "   • 测试无密码连接"
echo "   • 更新本地配置"
echo ""
echo "3. 完成后测试:"
echo "   ssh mi-pad"
echo "============"

echo "✅ SSH配置修复完成!"