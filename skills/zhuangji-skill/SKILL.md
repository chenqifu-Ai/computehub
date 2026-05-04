# 🚀 装机技能

## 多设备OpenClaw自动化部署装机技能

### 功能描述
自动化完成OpenClaw在多设备间的完整配置复制和部署，支持Android和Linux设备。包含SSH密钥同步和Git环境配置功能。

### 适用场景
- 新设备OpenClaw部署
- 多设备配置同步
- 灾备环境搭建
- 测试环境复制
- SSH密钥统一管理
- Git开发环境配置

### 快速开始
```bash
# 部署到指定设备
./deploy.sh 192.168.1.19 8022 u0_a207 123 18789

# 使用本地资源部署（优先本地包）
./deploy_local.sh 192.168.1.19 8022 u0_a213 123 18789

# 快速部署到192.168.1.19（固定配置）
./deploy_192.168.1.19.sh

# 批量部署多设备  
./batch_deploy.sh
```

### 配置参数
- `--target`: 目标设备地址 (必填)
- `--port`: SSH端口 (默认: 8022)
- `--user`: 用户名 (默认: u0_a207) 
- `--password`: 密码 (默认: 123)
- `--gateway-port`: Gateway端口 (默认: 18789)
- `--version`: OpenClaw版本 (默认: openclaw@2016.3.13)
- `--ssh-key-type`: SSH密钥类型 (默认: ed25519)
- `--git-user`: Git用户名 (默认: OpenClaw User)
- `--git-email`: Git邮箱 (默认: openclaw@example.com)

### 新功能特性

#### SSH 密钥管理
- **自动密钥生成**: 如不存在则自动生成 ED25519 密钥
- **安全同步**: 加密传输和权限设置
- **指纹验证**: 显示密钥指纹确认安全性
- **多设备统一**: 确保所有设备使用相同密钥

#### Git 环境集成
- **全局配置**: 自动设置用户名和邮箱
- **SSH 关联**: 配置 Git 使用指定 SSH 密钥
- **开发就绪**: 部署完成后即可进行 Git 操作

#### 本地资源部署说明
- **优先使用本地包**: 脚本会检查本地npm缓存中的OpenClaw包
- **避免网络下载**: 尽量使用本地资源，减少网络依赖
- **指定版本**: 默认使用openclaw@2016.3.13版本
- **快速部署**: 提供固定配置的快速部署脚本

### 文件结构
```
device-deployment/
├── SKILL.md          # 技能说明
├── deploy.sh         # 主部署脚本
├── deploy_local.sh   # 本地资源部署脚本
├── deploy_192.168.1.19.sh # 快速部署脚本
├── batch_deploy.sh   # 批量部署脚本
├── config_check.py   # 配置检查
├── sync_tool.py      # 同步工具
├── validation.py     # 验证工具
└── examples/         # 使用示例
```

### 依赖要求
- OpenClaw 2026.3.28+
- SSH客户端访问权限
- 目标设备Node.js环境

### 版本历史
- v1.0.0 (2026-04-01): 初始版本发布

---
*技能ID: zhuangji-skill*
*分类: 系统管理/装机*
*状态: ✅ 生产就绪*