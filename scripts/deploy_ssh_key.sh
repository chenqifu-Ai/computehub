#!/bin/bash
# OpenClaw SSH密钥部署脚本
# 用于在192.168.1.19上部署公钥

HOST="192.168.1.19"
PORT="8022"
USER="u0_a207"
PASSWORD="123"

# 读取公钥
PUBLIC_KEY=$(cat ~/.ssh/id_ed25519.pub)

# 部署公钥到远程服务器
echo "部署SSH公钥到 ${USER}@${HOST}:${PORT}..."

sshpass -p "${PASSWORD}" ssh -p "${PORT}" "${USER}@${HOST}" << EOF
    # 创建.ssh目录（如果不存在）
    mkdir -p ~/.ssh
    chmod 700 ~/.ssh
    
    # 备份原有的authorized_keys
    if [ -f ~/.ssh/authorized_keys ]; then
        cp ~/.ssh/authorized_keys ~/.ssh/authorized_keys.backup.$(date +%Y%m%d_%H%M%S)
    fi
    
    # 添加新的公钥
    echo "${PUBLIC_KEY}" >> ~/.ssh/authorized_keys
    chmod 600 ~/.ssh/authorized_keys
    
    echo "SSH公钥部署完成"
    echo "已添加密钥: ${PUBLIC_KEY}"
EOF

if [ $? -eq 0 ]; then
    echo "✅ 公钥部署成功"
    echo "测试无密码连接..."
    
    # 测试无密码连接
    ssh -p "${PORT}" "${USER}@${HOST}" "echo '无密码连接测试成功'"
    
    if [ $? -eq 0 ]; then
        echo "🎉 SSH密钥认证配置完成！"
    else
        echo "⚠️  无密码连接测试失败，请检查配置"
    fi
else
    echo "❌ 公钥部署失败"
    exit 1
fi
