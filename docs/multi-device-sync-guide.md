# 🔄 多设备协同机制指南

## 🎯 设计目标

### 解决单点故障问题
- **设备丢失防护**: 避免单设备故障导致系统瘫痪
- **数据冗余备份**: 多设备间实时数据同步
- **自动故障转移**: 主设备故障时自动切换到备用设备
- **状态监控预警**: 实时监控设备状态，提前预警

## 🏗️ 系统架构

### 三层防护体系
```
        [应用层]
           │
           ▼
    [同步管理层] ←→ [设备监控层]
           │
           ▼
      [存储层]
```

### 核心组件
1. **同步配置管理**: 同步策略、内容、频率配置
2. **设备注册系统**: 设备信息、状态、角色管理  
3. **自动同步引擎**: 定时数据同步和备份
4. **状态监控系统**: 设备健康状态实时监控
5. **故障转移机制**: 自动切换和恢复

## 🔧 配置说明

### 同步配置 (`sync-config.json`)
```json
{
  "sync_interval": 3600,      // 同步间隔(秒)
  "retention_days": 7,        // 备份保留天数
  "max_devices": 5,           // 最大设备数量
  "auto_failover": true,      // 自动故障转移
  "sync_content": {           // 同步内容
    "workspace": true,
    "config": true,
    "extensions": true,
    "agents": true,
    "memory": true,
    "skills": true
  }
}
```

### 设备注册 (`device-registry.json`)
```json
[
  {
    "device_id": "primary-termux",
    "ip_address": "192.168.1.9", 
    "username": "u0_a46",
    "status": "active",
    "last_sync": "2026-04-11T08:06:00+08:00",
    "role": "primary"
  }
]
```

## 🚀 使用流程

### 1. 添加新设备
```bash
# 手动添加设备到注册表
jq '. += [{"device_id": "new-tablet", "ip_address": "192.168.1.20", "username": "u0_a207", "status": "pending", "role": "backup"}]' device-registry.json > temp.json && mv temp.json device-registry.json
```

### 2. 配置同步
```bash
# 修改同步配置
jq '.multi_device_sync.sync_interval = 1800' sync-config.json > temp.json && mv temp.json sync-config.json
```

### 3. 启动同步
```bash
# 手动执行同步
/root/.openclaw/sync/auto-sync.sh

# 监控设备状态  
/root/.openclaw/sync/device-monitor.sh
```

### 4. 设置定时任务
```bash
# 每小时同步一次
termux-job-scheduler --script /root/.openclaw/sync/auto-sync.sh --periodic --period 3600000

# 每30分钟监控一次
termux-job-scheduler --script /root/.openclaw/sync/device-monitor.sh --periodic --period 1800000
```

## 🛡️ 故障处理

### 设备离线处理
1. **检测离线**: 监控脚本发现设备离线
2. **状态更新**: 将设备状态标记为offline
3. **警报通知**: 发送设备离线警报
4. **故障转移**: 如果主设备离线，切换到备用设备

### 数据同步失败
1. **重试机制**: 自动重试3次
2. **降级处理**: 部分同步失败仍继续其他同步
3. **日志记录**: 详细记录同步错误信息
4. **人工干预**: 重大错误需要人工处理

### 网络中断
1. **本地备份**: 网络中断时先做本地备份
2. **队列管理**: 网络恢复后重新同步
3. **增量同步**: 只同步变化部分，减少流量

## 📊 监控预警

### 监控指标
- **设备在线状态**: 心跳检测
- **同步成功率**: 同步任务完成情况  
- **数据一致性**: 设备间数据差异检查
- **存储空间**: 备份文件大小监控

### 预警规则
- 🔴 **紧急**: 主设备离线超过1小时
- 🟠 **警告**: 同步连续失败3次
- 🟡 **注意**: 存储空间使用超过80%
- 🔵 **信息**: 新设备成功注册

## 🔄 恢复流程

### 新设备加入
1. **设备注册**: 添加新设备到注册表
2. **初始同步**: 完整数据同步到新设备
3. **状态验证**: 检查数据完整性和一致性
4. **角色分配**: 分配主备角色

### 故障设备替换
1. **设备下线**: 将故障设备标记为离线
2. **数据清理**: 清理故障设备相关数据
3. **新设备加入**: 添加替换设备
4. **数据恢复**: 从备份恢复数据到新设备

## 💡 最佳实践

### 设备规划
- **主设备**: 性能最好，稳定性最高的设备
- **备用设备**: 至少1台备用设备
- **测试设备**: 用于测试新配置的设备

### 同步策略
- **频繁同步**: 重要数据每小时同步
- **完整备份**: 每天一次完整备份
- **版本控制**: 保留7天内的备份版本

### 安全考虑
- **加密传输**: 同步数据加密
- **权限控制**: 设备访问权限管理
- **审计日志**: 所有操作记录日志

## 🚨 紧急操作

### 手动故障转移
```bash
# 将主设备标记为离线
jq 'map(if .role == "primary" then .status = "offline" else . end)' device-registry.json > temp.json >& mv temp.json device-registry.json

# 提升备用设备为主设备
jq 'map(if .device_id == "backup-device" then .role = "primary" | .status = "active" else . end)' device-registry.json > temp.json >& mv temp.json device-registry.json
```

### 强制同步
```bash
# 忽略错误强制同步
/root/.openclaw/sync/auto-sync.sh --force
```

---
**最后更新**: 2026-04-11
**系统状态**: ✅ 正常运行
**设备数量**: 1台 (需要添加备用设备)