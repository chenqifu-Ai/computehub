# 🚀 ComputeHub Gateway - Ubuntu 部署指南

## 📋 系统要求

- **操作系统**: Ubuntu 20.04+ / Debian 11+
- **架构**: ARM64 (aarch64) 或 AMD64 (x86_64)
- **内存**: 最少 2GB，推荐 4GB+
- **磁盘**: 最少 1GB 可用空间
- **权限**: root 或 sudo 权限

## 🚀 快速部署

```bash
# 1. 上传部署包到服务器
scp -r deploy/ubuntu user@ubuntu-server:/tmp/

# 2. SSH 连接到服务器
ssh user@ubuntu-server

# 3. 执行部署脚本
sudo /tmp/deploy/ubuntu/scripts/deploy.sh
```

## ⚙️ 配置说明

### 环境变量配置
编辑 `/opt/computehub/config/.env`:
```bash
# ComputeHub API Key (可选)
# COMPUTEHUB_API_KEY="your-api-key-here"

# Ollama 本地 API (可选)
# OLLAMA_API_URL="http://localhost:11434/v1"
```

### 配置文件
编辑 `/opt/computehub/config/config.json`:
```json
{
  "composer": {
    "api_url": "http://localhost:11434/v1",
    "api_key": "",
    "model": "deepseek-v4-flash",
    "execute_models": ["deepseek-v4-flash", "qwen3.6-35b", "llama3.1:8b"]
  }
}
```

## 🛠️ 管理服务

```bash
# 启动服务
sudo systemctl start computehub-gateway

# 停止服务
sudo systemctl stop computehub-gateway

# 重启服务
sudo systemctl restart computehub-gateway

# 查看状态
sudo systemctl status computehub-gateway

# 设置开机自启
sudo systemctl enable computehub-gateway

# 查看日志
sudo journalctl -u computehub-gateway -f
```

## 📊 验证部署

```bash
# 健康检查
curl http://localhost:8282/api/health

# 节点列表
curl http://localhost:8282/api/v1/nodes/list

# 查看 Gateway 版本
curl http://localhost:8282/api/status
```

## 🐛 故障排查

### 服务无法启动
```bash
# 查看详细错误
sudo journalctl -u computehub-gateway -n 100

# 检查端口占用
sudo netstat -tulpn | grep 8282

# 检查文件权限
ls -la /opt/computehub/bin/
```

### 内存不足
```bash
# 监控内存使用
free -h

# 查看进程内存
ps aux | grep computehub
```

### Ollama 配置 (AI 功能)
```bash
# 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 拉取模型
ollama pull deepseek-v4-flash
ollama pull qwen3.6-35b

# 验证
curl http://localhost:11434/api/tags
```

## 📁 目录结构

```
/opt/computehub/
├── bin/                    # 可执行文件
│   ├── computehub-gateway
│   └── computehub-worker
├── config/                 # 配置文件
│   ├── config.json
│   └── .env
├── data/                   # 运行时数据
└── logs/                   # 日志文件
```

## 🔄 升级步骤

```bash
# 1. 停止服务
sudo systemctl stop computehub-gateway

# 2. 备份配置
sudo cp /opt/computehub/config/config.json /opt/computehub/config/config.json.bak

# 3. 替换二进制文件
sudo cp computehub-gateway-v0.7.2 /opt/computehub/bin/
sudo chown compute:compute /opt/computehub/bin/computehub-gateway

# 4. 启动服务
sudo systemctl start computehub-gateway

# 5. 验证
curl http://localhost:8282/api/health
```

## 📞 技术支持

- **文档**: `/opt/computehub/docs/`
- **日志**: `/opt/computehub/logs/`
- **配置文件**: `/opt/computehub/config/`
- **升级路线**: [UPGRADE_ROADMAP.md](https://github.com/chenqifu-Ai/computehub/blob/master/UPGRADE_ROADMAP.md)

---

**版本**: v0.7.1
**最后更新**: 2026-05-08
