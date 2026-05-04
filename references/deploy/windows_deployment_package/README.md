# 🪟 Windows OpenClaw部署包

## 快速开始

### 1. 复制文件到Windows设备
将整个 `windows_deployment_package` 文件夹复制到Windows桌面

### 2. 以管理员身份运行
右键点击 `deploy.bat` → "以管理员身份运行"

### 3. 等待部署完成
脚本会自动完成所有安装和配置步骤

## 📁 文件说明

- `deploy.bat` - 主部署脚本
- `install_node.js` - Node.js安装脚本（备用）
- `config_backup.bat` - 配置备份脚本
- `service_manager.bat` - 服务管理脚本
- `README.md` - 说明文档

## 🚀 部署流程

### 自动步骤
1. ✅ Node.js环境检查
2. ✅ OpenClaw安装
3. ✅ 配置目录初始化
4. ✅ Gateway服务启动
5. ✅ 部署结果验证

### 手动验证
部署完成后访问：
- **本地**: http://localhost:18789/health
- **远程**: http://[你的IP]:18789/health
- **预期响应**: `{"ok":true,"status":"live"}`

## 🛠️ 故障排除

### 常见问题
1. **Node.js未安装** - 运行 `install_node.js`
2. **端口冲突** - 修改 `deploy.bat` 中的端口号
3. **权限不足** - 以管理员身份运行

### 日志文件
部署日志保存在：`%TEMP%\openclaw_deploy.log`

## 📞 支持

如有问题，检查：
- Windows防火墙设置
- Node.js安装状态
- 网络连接

---
*部署包版本: 1.0.0*
*生成时间: 2026-04-01*