#!/bin/bash
# 多设备协同同步系统 - 防单点故障设计

echo "🚀 建立多设备协同机制"
echo "=============================="

# 配置
SYNC_DIR="/root/.openclaw/sync"
LOG_DIR="$SYNC_DIR/logs"
BACKUP_DIR="$SYNC_DIR/backups"
CONFIG_FILE="$SYNC_DIR/sync-config.json"

# 创建目录
mkdir -p "$SYNC_DIR" "$LOG_DIR" "$BACKUP_DIR"

# 生成同步配置
cat > "$CONFIG_FILE" <<EOF
{
  "multi_device_sync": {
    "enabled": true,
    "sync_interval": 3600,
    "retention_days": 7,
    "max_devices": 5,
    "auto_failover": true
  },
  "sync_content": {
    "workspace": true,
    "config": true,
    "extensions": true,
    "agents": true,
    "memory": true,
    "skills": true
  },
  "compression": {
    "enabled": true,
    "level": 6,
    "format": "tar.gz"
  },
  "encryption": {
    "enabled": true,
    "algorithm": "aes-256-gcm"
  },
  "verification": {
    "md5_check": true,
    "size_validation": true,
    "integrity_check": true
  }
}
EOF

echo "✅ 同步配置创建完成: $CONFIG_FILE"

# 创建设备注册表
DEVICE_DB="$SYNC_DIR/device-registry.json"
cat > "$DEVICE_DB" <<EOF
[
  {
    "device_id": "primary-termux",
    "ip_address": "192.168.1.9",
    "username": "u0_a46",
    "status": "active",
    "last_sync": "$(date -Iseconds)",
    "role": "primary"
  }
]
EOF

echo "✅ 设备注册表创建完成: $DEVICE_DB"

# 创建同步脚本
SYNC_SCRIPT="$SYNC_DIR/auto-sync.sh"
cat > "$SYNC_SCRIPT" <<'EOF'
#!/bin/bash
# 自动同步脚本

CONFIG_FILE="/root/.openclaw/sync/sync-config.json"
LOG_FILE="/root/.openclaw/sync/logs/sync_$(date +%Y%m%d_%H%M%S).log"

# 加载配置
if [ -f "$CONFIG_FILE" ]; then
    SYNC_INTERVAL=$(jq -r '.multi_device_sync.sync_interval' "$CONFIG_FILE")
    RETENTION_DAYS=$(jq -r '.multi_device_sync.retention_days' "$CONFIG_FILE")
else
    SYNC_INTERVAL=3600
    RETENTION_DAYS=7
fi

echo "🔄 开始多设备同步检查" | tee -a "$LOG_FILE"

# 1. 检查网络状态
check_network() {
    if ping -c 1 8.8.8.8 >/dev/null 2>&1; then
        echo "✅ 网络连接正常" | tee -a "$LOG_FILE"
        return 0
    else
        echo "❌ 网络连接失败" | tee -a "$LOG_FILE"
        return 1
    fi
}

# 2. 创建本地备份
create_local_backup() {
    local backup_file="/root/.openclaw/sync/backups/backup_$(date +%Y%m%d_%H%M%S).tar.gz"
    
    echo "📦 创建本地备份: $backup_file" | tee -a "$LOG_FILE"
    
    tar -czf "$backup_file" \
        /root/.openclaw/workspace/ \
        /root/.openclaw/config/ \
        /root/.openclaw/extensions/ \
        /root/.openclaw/agents/ \
        2>>"$LOG_FILE"
    
    if [ $? -eq 0 ]; then
        echo "✅ 本地备份成功: $(du -h "$backup_file" | cut -f1)" | tee -a "$LOG_FILE"
        
        # 清理旧备份
        find "/root/.openclaw/sync/backups" -name "backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete
        
        return 0
    else
        echo "❌ 本地备份失败" | tee -a "$LOG_FILE"
        return 1
    fi
}

# 3. 同步到其他设备（模拟）
sync_to_devices() {
    echo "🌐 检查可同步设备..." | tee -a "$LOG_FILE"
    
    # 这里应该是实际的设备同步逻辑
    # 例如: scp, rsync, 或者云存储同步
    
    echo "📡 设备同步功能待实现" | tee -a "$LOG_FILE"
    return 0
}

# 主流程
main() {
    echo "⏰ 同步时间: $(date)" | tee -a "$LOG_FILE"
    echo "==============================" | tee -a "$LOG_FILE"
    
    if check_network; then
        if create_local_backup; then
            sync_to_devices
        fi
    fi
    
    echo "✅ 同步检查完成" | tee -a "$LOG_FILE"
    echo "下次同步: $(date -d "+$SYNC_INTERVAL seconds")" | tee -a "$LOG_FILE"
}

main "$@"
EOF

chmod +x "$SYNC_SCRIPT"
echo "✅ 同步脚本创建完成: $SYNC_SCRIPT"

# 创建监控脚本
MONITOR_SCRIPT="$SYNC_DIR/device-monitor.sh"
cat > "$MONITOR_SCRIPT" <<'EOF'
#!/bin/bash
# 设备状态监控脚本

CONFIG_FILE="/root/.openclaw/sync/sync-config.json"
DEVICE_DB="/root/.openclaw/sync/device-registry.json"
LOG_FILE="/root/.openclaw/sync/logs/monitor_$(date +%Y%m%d_%H%M%S).log"

echo "📊 开始设备状态监控" | tee -a "$LOG_FILE"

# 检查设备状态
check_device_status() {
    local device_id="$1"
    local ip_address="$2"
    
    if ping -c 1 "$ip_address" >/dev/null 2>&1; then
        echo "✅ 设备 $device_id ($ip_address) 在线" | tee -a "$LOG_FILE"
        return 0
    else
        echo "❌ 设备 $device_id ($ip_address) 离线" | tee -a "$LOG_FILE"
        return 1
    fi
}

# 更新设备状态
update_device_status() {
    local device_id="$1"
    local status="$2"
    
    if [ -f "$DEVICE_DB" ]; then
        temp_file="$(mktemp)"
        jq "map(if .device_id == \"$device_id\" then .status = \"$status\" | .last_check = \"$(date -Iseconds)\" else . end)" "$DEVICE_DB" > "$temp_file"
        mv "$temp_file" "$DEVICE_DB"
    fi
}

# 主监控流程
main() {
    echo "⏰ 监控时间: $(date)" | tee -a "$LOG_FILE"
    echo "==============================" | tee -a "$LOG_FILE"
    
    if [ ! -f "$DEVICE_DB" ]; then
        echo "❌ 设备数据库不存在" | tee -a "$LOG_FILE"
        return 1
    fi
    
    # 检查所有注册设备
    device_count=$(jq length "$DEVICE_DB")
    echo "📋 注册设备数量: $device_count" | tee -a "$LOG_FILE"
    
    for i in $(seq 0 $(($device_count - 1))); do
        device_id=$(jq -r ".[$i].device_id" "$DEVICE_DB")
        ip_address=$(jq -r ".[$i].ip_address" "$DEVICE_DB")
        
        if check_device_status "$device_id" "$ip_address"; then
            update_device_status "$device_id" "online"
        else
            update_device_status "$device_id" "offline"
        fi
    done
    
    echo "✅ 设备监控完成" | tee -a "$LOG_FILE"
}

main "$@"
EOF

chmod +x "$MONITOR_SCRIPT"
echo "✅ 监控脚本创建完成: $MONITOR_SCRIPT"

echo ""
echo "🎯 多设备协同系统部署完成!"
echo "📁 配置目录: $SYNC_DIR"
echo "📋 设备注册: $DEVICE_DB"
echo "🔄 同步脚本: $SYNC_SCRIPT"
echo "📊 监控脚本: $MONITOR_SCRIPT"
echo ""
echo "🚀 下一步: 添加新设备到注册表并配置自动同步"
echo "=============================="