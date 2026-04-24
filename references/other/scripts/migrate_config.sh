#!/bin/bash
# 配置迁移脚本 - 从本机迁移到 10.35.204.186

echo "🚀 配置迁移脚本"
echo "================================"
echo "源: 本机配置"
echo "目标: 10.35.204.186"
echo "================================"

# 检查目标设备
echo "🔍 检查目标设备..."
if ! ping -c 2 10.35.204.186 >/dev/null 2>&1; then
    echo "❌ 目标设备离线"
    exit 1
fi

echo "✅ 目标设备在线"

# 清理 SSH 主机密钥
echo "🔧 清理 SSH 主机密钥..."
ssh-keygen -R "[10.35.204.186]:8022" 2>/dev/null
ssh-keyscan -p 8022 10.35.204.186 2>/dev/null >> ~/.ssh/known_hosts

echo "✅ SSH 配置完成"

# 迁移函数
migrate_config() {
    echo "📦 开始配置迁移..."
    
    # 创建配置压缩包
    echo "1. 打包本机配置..."
    tar -czf /tmp/openclaw_config.tar.gz -C /root/.openclaw . 2>/dev/null
    
    # 传输配置
    echo "2. 传输配置到目标设备..."
    sshpass -p '123' scp -P 8022 /tmp/openclaw_config.tar.gz u0_a165@10.35.204.186:/data/data/com.termux/files/home/
    
    # 在目标设备上解压配置
    echo "3. 在目标设备上部署配置..."
    sshpass -p '123' ssh -p 8022 u0_a165@10.35.204.186 << 'EOF'
    
    echo "📦 解压配置..."
    if [ -f ~/openclaw_config.tar.gz ]; then
        # 备份现有配置
        if [ -d ~/.openclaw ]; then
            mv ~/.openclaw ~/.openclaw.backup.$(date +%s)
            echo "✅ 现有配置已备份"
        fi
        
        # 创建目录并解压
        mkdir -p ~/.openclaw
        tar -xzf ~/openclaw_config.tar.gz -C ~/.openclaw
        rm ~/openclaw_config.tar.gz
        
        echo "✅ 配置解压完成"
        echo "配置文件数: $(find ~/.openclaw -type f | wc -l)"
    else
        echo "❌ 配置包未找到"
        exit 1
    fi
    
    echo ""
    echo "🔧 配置权限设置..."
    chmod -R 755 ~/.openclaw
    
    echo ""
    echo "✅ 配置迁移完成!"
    echo "新配置位置: ~/.openclaw"
    echo "备份位置: ~/.openclaw.backup.*"
EOF
}

# 执行迁移
migrate_config

# 清理临时文件
rm -f /tmp/openclaw_config.tar.gz

echo ""
echo "🎯 迁移结果验证:"
echo "================================"

# 验证迁移结果
if sshpass -p '123' ssh -p 8022 u0_a165@10.35.204.186 "[ -d ~/.openclaw ] && echo '✅ 配置目录存在' || echo '❌ 配置目录缺失'"; then
    echo "✅ 配置迁移验证成功!"
    
    # 显示配置信息
    sshpass -p '123' ssh -p 8022 u0_a165@10.35.204.186 "
        echo '📁 配置目录大小: $(du -sh ~/.openclaw | cut -f1)'
        echo '📊 文件数量: $(find ~/.openclaw -type f | wc -l)'
        echo '🔧 主要配置文件:'
        ls -la ~/.openclaw/ | grep -E '(openclaw.json|workspace|memory)' | head -5
    "
else
    echo "❌ 配置迁移验证失败"
fi

echo "================================"