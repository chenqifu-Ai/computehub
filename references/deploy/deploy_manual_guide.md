# 🪟 Windows OpenClaw手动部署指南

## 目标设备信息
- **IP地址**: 192.168.2.134
- **用户名**: administrator
- **密码**: c9fc9f,.
- **WinRM端口**: 5985 (已启用)

## 🔧 手动部署步骤

### 1. 在Windows设备上操作

#### 方法A: 使用批处理文件
1. **下载部署脚本**:
   ```cmd
   curl -o %TEMP%\deploy_openclaw.bat https://raw.githubusercontent.com/your-repo/deploy_openclaw.bat
   ```

2. **以管理员身份运行**:
   ```cmd
   %TEMP%\deploy_openclaw.bat
   ```

#### 方法B: 手动执行命令
```cmd
# 1. 安装Node.js (如果未安装)
# 访问 https://nodejs.org 下载并安装Node.js 20+

# 2. 安装OpenClaw
npm install -g openclaw@latest

# 3. 初始化配置
openclaw setup

# 4. 启动服务
node -e "require('openclaw').startGateway({port: 18789})"

# 5. 验证服务
curl http://localhost:18789/health
```

### 2. 部署验证
服务启动后，访问以下URL验证：
- **健康检查**: http://192.168.2.134:18789/health
- **预期响应**: `{"ok":true,"status":"live"}`

### 3. 配置同步（可选）
如果需要同步当前环境的配置：

```powershell
# 从当前设备复制配置
# 需要手动将 ~/.openclaw/workspace 目录复制到Windows的 %USERPROFILE%\.openclaw\workspace

# 或者重新配置Windows环境
openclaw setup
```

## 🛠️ 故障排除

### 常见问题1: Node.js未安装
```cmd
# 解决方案: 手动安装Node.js
# 1. 访问 https://nodejs.org/dist/v20.11.1/node-v20.11.1-x64.msi
# 2. 下载并安装
# 3. 重新打开命令提示符
```

### 常见问题2: 端口冲突
```cmd
# 解决方案: 使用不同端口
node -e "require('openclaw').startGateway({port: 18888})"
```

### 常见问题3: 权限不足
```cmd
# 解决方案: 以管理员身份运行命令提示符
# 右键点击"命令提示符" → "以管理员身份运行"
```

## 📞 技术支持

如果遇到问题，可以：
1. 检查Windows防火墙设置
2. 确认Node.js安装正确
3. 验证OpenClaw安装: `openclaw --version`
4. 查看服务日志

## ✅ 完成验证
部署完成后，请验证：
- [ ] Node.js已安装 (`node --version`)
- [ ] OpenClaw已安装 (`openclaw --version`)
- [ ] 服务正常运行 (`http://192.168.2.134:18789/health`)
- [ ] 可以远程访问

---
*部署指南生成时间: 2026-04-01 10:40*
*目标设备: 192.168.2.134*