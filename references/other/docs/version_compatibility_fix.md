# 🔄 OpenClaw版本兼容性修复方案

## 📊 问题诊断

### 设备信息
- **TUI客户端**: 192.168.1.19 (小米手机 M2105K81AC)
- **TUI版本**: OpenClaw 2026.3.31
- **当前环境**: OpenClaw 2026.3.13
- **问题**: 配置版本不兼容，配对需要重新批准

## 🎯 解决方案

### 方案1: 升级当前环境（推荐）
```bash
# 在Termux环境中升级OpenClaw
pkg update
pkg upgrade
npm update -g openclaw

# 或者重新安装最新版本
npm uninstall -g openclaw
npm install -g openclaw@latest
```

### 方案2: 设备重新配对
```bash
# 1. 首先在小米手机上批准当前设备的配对请求
#    在小米手机上运行: openclaw devices list
#    找到并批准当前设备的请求ID

# 2. 或者移除现有配对并重新建立
openclaw devices remove 0a743e5065599eed968e6f16034bd3327a511994d12c372c054d651cd7e2bcb4

# 3. 重新初始化配对流程
openclaw devices pair
```

### 方案3: 配置版本兼容性处理
```bash
# 手动修改配置版本信息
sed -i 's/"lastTouchedVersion": "2026.3.31"/"lastTouchedVersion": "2026.3.13"/g' ~/.openclaw/openclaw.json
sed -i 's/"lastRunVersion": "2026.3.31"/"lastRunVersion": "2026.3.13"/g' ~/.openclaw/openclaw.json
```

## 🔧 详细步骤

### 步骤1: 连接到小米手机
```bash
# 通过SSH连接到小米手机
sshpass -p 123 ssh -p 8022 u0_a207@192.168.1.19

# 检查OpenClaw版本
openclaw --version

# 查看设备配对状态
openclaw devices list
```

### 步骤2: 在小米手机上批准配对
```bash
# 在小米手机上运行以下命令查看待批准设备
openclaw devices list

# 找到当前设备的请求ID并批准
openclaw devices approve <request-id>
```

### 步骤3: 验证连接
```bash
# 使用修复后的启动脚本
~/start_openclaw.sh tui

# 或者直接指定连接参数
openclaw tui --host 192.168.1.19 --port 18789
```

## 📋 执行计划

### 立即执行 (现在)
1. [ ] SSH连接到小米手机 192.168.1.19
2. [ ] 检查OpenClaw版本确认是 2026.3.31
3. [ ] 运行 `openclaw devices list` 查看待批准请求

### 短期执行 (10分钟内)
4. [ ] 批准当前设备的配对请求
5. [ ] 验证TUI连接恢复正常
6. [ ] 测试双向通信功能

### 长期解决方案 (24小时内)
7. [ ] 统一所有设备OpenClaw版本
8. [ ] 建立版本管理流程
9. [ ] 配置自动升级机制

## 🌐 网络连接配置

### 小米手机信息
- **IP**: 192.168.1.19
- **SSH端口**: 8022
- **用户名**: u0_a207
- **密码**: 123
- **Gateway端口**: 18789

### 连接命令
```bash
# SSH连接
sshpass -p 123 ssh -p 8022 u0_a207@192.168.1.19

# 检查服务状态
curl http://192.168.1.19:18789/api/status

# TUI连接
openclaw tui --host 192.168.1.19 --port 18789
```

## ⚠️ 注意事项

1. **备份配置**: 修改前备份所有配置文件
2. **网络稳定性**: 确保192.168.1.19设备网络稳定
3. **防火墙设置**: 检查端口8022和18789的防火墙规则
4. **版本一致性**: 最终目标所有设备版本统一

## 🔍 故障排除

### 常见问题
1. **配对超时**: 检查网络连接，重新启动配对流程
2. **版本拒绝**: 升级或降级到兼容版本
3. **连接失败**: 验证防火墙和端口配置

### 调试命令
```bash
# 检查网络连通性
ping 192.168.1.19

# 检查端口开放
nc -zv 192.168.1.19 8022
nc -zv 192.168.1.19 18789

# 查看日志
openclaw gateway logs
```

---
**创建时间**: 2026-04-02 07:05
**预计解决**: 2026-04-02 07:30
**负责人**: 小智
**状态**: 🟡 处理中