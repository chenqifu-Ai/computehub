# 🪟 Windows OpenClaw部署技能

## Windows设备自动化部署装机技能

### 功能描述
自动化完成OpenClaw在Windows设备上的完整部署和配置同步，支持远程Windows设备。

### 适用场景
- Windows设备OpenClaw部署
- Windows与Linux/Android设备配置同步
- 跨平台环境搭建

### 快速开始
```bash
# 部署到Windows设备
./deploy_windows.ps1 192.168.1.100 administrator password123

# 使用RDP远程部署
./deploy_rdp.ps1 192.168.1.100 administrator password123
```

### 配置参数
- `--computer`: 目标Windows计算机名或IP (必填)
- `--username`: 管理员用户名 (默认: administrator)
- `--password`: 管理员密码 (必填)
- `--port`: WinRM端口 (默认: 5985)

### 文件结构
```
windows-deployment/
├── SKILL.md          # 技能说明
├── deploy_windows.ps1 # PowerShell主部署脚本
├── deploy_rdp.ps1    # RDP远程部署脚本
├── config_check.ps1  # Windows配置检查
├── sync_tool.ps1     # Windows同步工具
├── validation.ps1    # Windows验证工具
└── examples/         # 使用示例
```

### 依赖要求
- Windows PowerShell 5.1+
- WinRM服务启用
- 管理员权限
- Node.js 18+

### 版本历史
- v1.0.0 (2026-04-01): 初始版本发布

---
*技能ID: windows-deployment-skill*
*分类: 系统管理/Windows装机*
*状态: ✅ 生产就绪*