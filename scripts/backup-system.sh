#!/bin/bash
# OpenClaw 完整备份系统
# 三重备份保障机制

echo "🔐 OpenClaw 系统备份启动"
echo "=============================="
echo "备份时间: $(date)"
echo "备份主机: $(hostname)"
echo ""

# 备份配置
BACKUP_DIR="/root/.openclaw/backups"
SNAPSHOT_DIR="$BACKUP_DIR/snapshots"
LOG_DIR="$BACKUP_DIR/logs"
RETENTION_DAYS=7

# 创建目录
mkdir -p "$BACKUP_DIR" "$SNAPSHOT_DIR" "$LOG_DIR"

# 生成备份文件名
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$SNAPSHOT_DIR/openclaw_backup_$TIMESTAMP.tar.gz"
LOG_FILE="$LOG_DIR/backup_$TIMESTAMP.log"

# 开始备份
echo "1. 📦 开始系统备份..." | tee -a "$LOG_FILE"

# 备份核心目录
echo "2. 📁 备份核心配置文件..." | tee -a "$LOG_FILE"
tar -czf "$BACKUP_FILE" \
    /root/.openclaw/workspace/ \
    /root/.openclaw/extensions/ \
    /root/.openclaw/config/ \
    /root/.openclaw/agents/ \
    --exclude="*/node_modules" \
    --exclude="*/.git" \
    --exclude="*/tmp" \
    --exclude="*/logs" 2>>"$LOG_FILE"

# 检查备份结果
if [ $? -eq 0 ]; then
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "✅ 备份成功: $BACKUP_FILE ($BACKUP_SIZE)" | tee -a "$LOG_FILE"
    
    # 计算MD5校验和
    MD5_SUM=$(md5sum "$BACKUP_FILE" | cut -d' ' -f1)
    echo "🔢 MD5校验和: $MD5_SUM" | tee -a "$LOG_FILE"
    
    # 记录备份元数据
    echo "{\"timestamp\": \"$(date)\", \"file\": \"$BACKUP_FILE\", \"size\": \"$BACKUP_SIZE\", \"md5\": \"$MD5_SUM\"}" >> "$BACKUP_DIR/backup_metadata.json"
    
else
    echo "❌ 备份失败! 查看日志: $LOG_FILE" | tee -a "$LOG_FILE"
    exit 1
fi

# 清理旧备份
echo ""
echo "3. 🗑️ 清理过期备份(保留$RETENTION_DAYS天)..." | tee -a "$LOG_FILE"
find "$SNAPSHOT_DIR" -name "openclaw_backup_*.tar.gz" -mtime +$RETENTION_DAYS -delete 2>>"$LOG_FILE"
find "$LOG_DIR" -name "backup_*.log" -mtime +$RETENTION_DAYS -delete 2>>"$LOG_FILE"

echo "✅ 清理完成" | tee -a "$LOG_FILE"

# 显示备份状态
echo ""
echo "4. 📊 备份状态汇总:" | tee -a "$LOG_FILE"
echo "   备份文件: $BACKUP_FILE" | tee -a "$LOG_FILE"
echo "   文件大小: $BACKUP_SIZE" | tee -a "$LOG_FILE"
echo "   MD5校验: $MD5_SUM" | tee -a "$LOG_FILE"
echo "   日志文件: $LOG_FILE" | tee -a "$LOG_FILE"

# 显示现有备份
echo ""
echo "5. 📋 现有备份列表:" | tee -a "$LOG_FILE"
ls -la "$SNAPSHOT_DIR" | grep "openclaw_backup_" | tee -a "$LOG_FILE"

echo ""
echo "=============================="
echo "🎯 OpenClaw 备份完成!"
echo "下次备份: 每日自动执行"
echo "备份保留: $RETENTION_DAYS 天"
echo "=============================="

# 设置备份成功标志
touch "$BACKUP_DIR/last_backup_success"

# 发送备份成功通知（可选）
# echo "✅ OpenClaw备份完成: $BACKUP_FILE ($BACKUP_SIZE)" | send-notification