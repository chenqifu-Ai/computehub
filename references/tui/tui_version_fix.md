# 🚨 TUI版本兼容性问题修复方案

## 🔍 问题分析

### 错误信息
```
Config was last written by a newer OpenClaw (2026.3.31); current version is 2026.3.13.
Pairing required. Run `openclaw devices list`, approve your request ID, then reconnect.
```

### 根本原因
1. **版本不匹配**: 某个配对设备运行 OpenClaw 2026.3.31
2. **配置冲突**: 新版本配置与当前版本 2026.3.13 不兼容
3. **配对问题**: 需要重新认证设备连接

## 🎯 解决方案

### 方案1: 升级当前环境（推荐）
```bash
# 升级OpenClaw到最新版本
npm update -g openclaw

# 或者重新安装
npm uninstall -g openclaw
npm install -g openclaw@latest
```

### 方案2: 重置设备配对
```bash
# 查看当前配对设备
openclaw devices list

# 移除问题设备
openclaw devices remove <device-id>

# 重新配对
openclaw devices pair
```

### 方案3: 清理并重建配置
```bash
# 备份当前配置
cp ~/.openclaw/openclaw.json ~/.openclaw/openclaw.json.backup

# 重置配置版本信息
sed -i 's/"2026.3.31"/"2026.3.13"/g' ~/.openclaw/openclaw.json

# 或者完全重置配置
openclaw config reset
```

## 🔧 详细步骤

### 步骤1: 识别问题设备
```bash
# 检查所有可能的配置文件
grep -r "2026.3.31" ~/.openclaw/ --include="*.json"

# 检查网络中的OpenClaw设备
nmap -p 18789 192.168.1.0/24 | grep open
```

### 步骤2: 升级或隔离
- **选项A**: 升级本机到 2026.3.31
- **选项B**: 降级问题设备到 2026.3.13  
- **选项C**: 隔离问题设备网络访问

### 步骤3: 重新配置TUI
```bash
# 确保TUI连接本地gateway
sed -i 's/192.168.*/127.0.0.1/g' ~/start_openclaw.sh

# 或者明确指定本地连接
~/start_openclaw.sh --host 127.0.0.1 --port 18789
```

## 📋 执行计划

### 立即执行 (5分钟内)
1. [ ] 备份当前配置
2. [ ] 检查问题设备IP
3. [ ] 尝试方案2（设备重置）

### 短期执行 (30分钟内)  
4. [ ] 如果方案2失败，执行方案1（升级）
5. [ ] 验证TUI连接正常
6. [ ] 更新所有设备版本一致性

### 长期预防
7. [ ] 建立版本管理流程
8. [ ] 配置自动升级机制
9. [ ] 设置版本兼容性检查

## ⚠️ 风险控制

### 回滚方案
```bash
# 如果升级出现问题
npm install -g openclaw@2026.3.13

# 恢复备份配置  
cp ~/.openclaw/openclaw.json.backup ~/.openclaw/openclaw.json
```

### 监控指标
- ✅ TUI连接成功率
- ✅ Gateway版本一致性  
- ✅ 设备配对状态
- ✅ 配置兼容性

## 📊 当前状态

- **本机版本**: 2026.3.13
- **问题版本**: 2026.3.31 (某个远程设备)
- **影响范围**: TUI客户端连接失败
- **紧急程度**: 🟡 中等 - 功能受限

---
**创建时间**: 2026-04-02 06:55
**负责人**: 小智
**预计解决时间**: 2026-04-02 07:30