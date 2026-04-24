# ⚡ 快速开始指南

## 立即部署步骤

### 1. 📁 复制文件到Windows
将整个文件夹复制到Windows桌面

### 2. 🚀 运行主部署脚本
右键点击 `deploy.bat` → "以管理员身份运行"

### 3. ⏳ 等待自动完成
脚本会自动执行以下步骤：
- ✅ 检查Node.js环境
- ✅ 安装OpenClaw
- ✅ 初始化配置  
- ✅ 启动服务
- ✅ 验证部署

### 4. ✅ 验证部署
访问: http://localhost:18789/health
预期响应: `{"ok":true,"status":"live"}`

## 🆘 常见问题解决

### 如果Node.js未安装：
1. 运行 `install_node.js`
2. 安装完成后重新运行 `deploy.bat`

### 如果端口冲突：
编辑 `deploy.bat`，修改端口号：
```bat
start "OpenClaw Gateway" /B node -e "require('openclaw').startGateway({port: 18888})"
```

### 如果权限不足：
- 以管理员身份运行所有脚本

## 🛠️ 工具说明

- `deploy.bat` - 主部署脚本
- `install_node.js` - Node.js安装器
- `service_manager.bat` - 服务管理
- `config_backup.bat` - 配置备份

## 📞 技术支持

部署完成后：
- 🌐 远程访问: http://[你的IP]:18789
- 📊 健康检查: http://localhost:18789/health
- 📝 查看日志: %TEMP%\\openclaw_deploy.log

---
*预计部署时间: 3-10分钟*
*开始时间: 现在*