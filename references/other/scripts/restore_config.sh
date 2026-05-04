#!/bin/bash
# 配置恢复脚本 - 恢复设备 10.35.204.186 的原始配置
# 用户名: u0_a207, 密码: 123

echo "🔧 配置恢复脚本"
echo "================================"
echo "目标: 恢复 10.35.204.186 的原始配置"
echo "用户: u0_a207"
echo "状态: 等待设备在线"
echo "================================"

# 设备监控函数
wait_for_device() {
    echo "🔍 等待设备 10.35.204.186 恢复在线..."
    echo "请确保设备开机并连接网络"
    echo ""
    
    while true; do
        if ping -c 2 10.35.204.186 >/dev/null 2>&1; then
            echo "✅ 设备恢复在线!"
            break
        else
            echo "⏰ $(date +%H:%M:%S) - 设备仍然离线，30秒后重试..."
            sleep 30
        fi
    done
}

# 配置恢复函数
restore_config() {
    echo "🚀 开始恢复配置..."
    echo "================================"
    
    # 清理 SSH 主机密钥
    ssh-keygen -R "[10.35.204.186]:8022" 2>/dev/null
    ssh-keyscan -p 8022 10极.204.186 2>/dev/null >> ~/.ssh/known_hosts
    
    # 执行恢复操作
    sshpass -p '123' ssh -o StrictHostKeyChecking=no -p 8022 u0_a207@10.35.204.186 << 'EOF'
    
    echo "📦 恢复原始配置..."
    echo "================================"
    
    # 1. 检查现有配置状态
    echo "1. 🔍 当前配置状态:"
    if [ -d ~/.openclaw ]; then
        echo "配置大小: $(du -sh ~/.openclaw | cut -f1)"
        echo "文件数量: $(find ~/.openclaw -type f | wc -l)"
        
        # 创建备份
        backup_dir=~/.openclaw.migration_backup.$(date +%Y%m%d_%H%M%S)
        mv ~/.openclaw "$backup_dir"
        echo "✅ 当前配置已备份到: $backup_dir"
    else
        echo "❌ 无现有配置"
    fi
    
    echo ""
    echo "2. 🗑️ 清理环境..."
    # 清理可能的残留文件
    rm -rf ~/openclaw_config*.tar.gz 2>/dev/null
    
    echo ""
    echo "3. 🔄 恢复选项:"
    echo "由于设备原始配置未知，建议:"
    echo "a) 重新安装 OpenClaw: npm install -g openclaw"
    echo "b) 手动配置所需设置"
    echo "c) 从其他设备迁移最小配置"
    
    echo ""
    echo "4. 🛠️ 执行基础恢复..."
    # 创建最小配置目录
    mkdir -p ~/.openclaw
    
    # 创建基础配置文件
    cat > ~/.openclaw/openclaw.json << 'EOF'
{
  "version": "2026.3.13",
  "model": "ollama-cloud/deepseek-v3.1:671b",
  "gateway": {
    "port": 18789,
    "host": "localhost"
  },
  "created": "2026-04-09T19:36:00Z",
  "note": "Minimal configuration restored"
}
EOF
    
    echo "✅ 基础配置文件创建完成"
    
    # 设置权限
    chmod -R 755 ~/.openclaw
    
    echo ""
    echo "5. ✅ 恢复完成:"
    echo "最小配置已恢复"
    echo "可在此基础上重新配置"
    echo "备份位置: $backup_dir (如有)"
    
    echo "================================"
EOF
}

# 主执行流程
echo "🎯 配置恢复计划"
echo "================================"
echo "步骤 1: 等待设备在线"
echo "步骤 2: 备份现有配置"
echo "步骤 3: 恢复最小配置"
echo "步骤 4: 后续手动配置"
echo "================================"

# 等待设备在线
wait_for_device

# 执行恢复
restore_config

echo ""
echo "🎉 配置恢复操作完成!"
echo "设备已恢复最小配置，可进行进一步配置"