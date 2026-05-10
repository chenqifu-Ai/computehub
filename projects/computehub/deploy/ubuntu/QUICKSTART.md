# ⚡ ComputeHub Gateway 快速部署指南

## 一键部署

```bash
# 1. 解压部署包
tar -xzf computehub-gateway-v0.7.1-ubuntu.tar.gz

# 2. 执行部署（需要 root 权限）
cd ubuntu
sudo bash scripts/deploy.sh
```

## 部署后验证

```bash
# 检查服务状态
sudo systemctl status computehub-gateway

# 测试 API
curl http://localhost:8282/api/health

# 预期输出:
# {"status":"ok","version":"v0.7.1","timestamp":"2026-05-08T..."}
```

## 配置修改

```bash
# 编辑配置文件
sudo nano /opt/computehub/config/config.json

# 编辑环境变量
sudo nano /opt/computehub/config/.env

# 重启服务生效
sudo systemctl restart computehub-gateway
```

## 常见问题

| 问题 | 解决方案 |
|------|----------|
| 服务无法启动 | 检查 `.env` 文件中的 API Key |
| 端口被占用 | 修改 config.json 中的 port 配置 |
| 权限错误 | 确认 `/opt/computehub` 所有权为 `compute:compute` |
| 内存不足 | 增加 Swap 或升级服务器配置 |

---

**部署时间**: < 5 分钟
**资源需求**: 2GB RAM, 1GB Disk, 1 CPU Core
