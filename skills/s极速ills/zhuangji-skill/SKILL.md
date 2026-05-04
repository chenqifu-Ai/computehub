# 🚀 装机技能

## 多设备OpenClaw自动化部署装机技能

### 功能描述
自动化完成OpenClaw在多设备间的完整配置复制和部署，支持Android和Linux设备。

### 适用场景
- 新设备OpenClaw部署
- 多设备配置同步
- 灾备环境搭建
- 测试环境复制

### 快速开始
```bash
# 部署到指定设备
./deploy.sh 192.168.1.19 8022 u0_a207 123 18789

# 批量部署多设备  
./batch_deploy.sh
```

### 配置参数
- `--target`: 目标设备地址 (必填)
- `--port`: SSH端口 (默认: 8022)
- `--user`: 用户名 (默认: u0_a207) 
- `--password`: 密码 (默认: 123)
- `--gateway-port`: Gateway端口 (默认: 18789)

### 文件结构
```
zhuangji-skill/
├── SKILL.md          # 技能说明
├── deploy.sh         # 主装机脚本
├── batch_deploy.sh   # 批量装机脚本
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