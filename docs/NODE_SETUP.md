# 🤖 ComputeHub 节点接入指南

本指南帮助你将算力节点（GPU 服务器）接入 ComputeHub 集群。

---

## 📋 前置要求

### 硬件要求

| 资源 | 最低要求 | 推荐配置 |
|------|----------|----------|
| **GPU** | 1x GTX 1060 | 1x RTX 3090 或更高 |
| **内存** | 8 GB | 32 GB+ |
| **存储** | 50 GB | 500 GB+ SSD |
| **网络** | 10 Mbps | 100 Mbps+ |

### 软件要求

- **操作系统**: Linux (Ubuntu 20.04+, CentOS 7+)
- **Python**: 3.10+
- **Docker**: 20.10+ (可选，用于容器化部署)
- **NVIDIA Driver**: 470+ (GPU 节点必需)

---

## 🚀 快速接入（3 步）

### Step 1: 克隆项目

```bash
# 在算力节点服务器上
git clone https://github.com/chenqifu-Ai/computehub.git
cd computehub
```

### Step 2: 一键接入

```bash
# 运行自动注册脚本
python node/join_cluster.py --gateway http://GATEWAY_IP:8000

# 示例：
python node/join_cluster.py --gateway http://192.168.1.100:8000
```

脚本会自动：
- ✅ 检测 GPU 型号和数量
- ✅ 检测 CPU 核心数和内存
- ✅ 生成节点名称
- ✅ 注册到 Gateway
- ✅ 保存节点配置

### Step 3: 启动服务

```bash
# 启动 Node Agent（接收任务）
python node/agent_api.py &

# 启动心跳服务（上报状态）
python node/heartbeat_client.py &
```

完成！节点已接入集群。

---

## 🔧 手动配置（可选）

### 安装依赖

```bash
# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装依赖
pip install fastapi uvicorn requests pynvml psutil
```

### 手动注册节点

```bash
curl -X POST http://GATEWAY_IP:8000/api/v1/nodes/register \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my-gpu-node-1",
    "gpu_model": "RTX 4090",
    "gpu_count": 1,
    "cpu_cores": 16,
    "memory_gb": 64,
    "country": "China",
    "city": "Beijing"
  }'
```

### 配置防火墙

确保以下端口可访问：

| 端口 | 用途 | 方向 |
|------|------|------|
| 8080 | Node Agent API | 入站（从 Gateway） |
| 8000 | Gateway API | 出站（到 Gateway） |

```bash
# Ubuntu (UFW)
ufw allow 8080/tcp
ufw allow out 8000/tcp

# CentOS (FirewallD)
firewall-cmd --add-port=8080/tcp --permanent
firewall-cmd --reload
```

---

## 📊 验证节点状态

### 在 Gateway 上查看

```bash
# 查看节点列表
curl http://GATEWAY_IP:8000/api/v1/nodes/

# 查看特定节点
curl http://GATEWAY_IP:8000/api/v1/nodes/YOUR_NODE_ID
```

### 在节点上查看

```bash
# 查看 Node Agent 状态
curl http://localhost:8080/health

# 查看性能指标
curl http://localhost:8080/metrics
```

---

## 🛠️ 故障排查

### 节点无法注册

**问题**: `Connection refused`

**解决**:
1. 检查 Gateway 是否运行：`curl http://GATEWAY_IP:8000/health`
2. 检查防火墙规则
3. 确认网络连通性：`ping GATEWAY_IP`

### 心跳失败

**问题**: `404 Node not found`

**解决**:
1. 确认节点 ID 正确
2. 重新运行 `join_cluster.py`
3. 检查 `node_config.json` 配置

### GPU 检测失败

**问题**: `GPU: Unknown` 或 `GPU: Error`

**解决**:
1. 安装 NVIDIA 驱动
2. 安装 `nvidia-ml-py`: `pip install nvidia-ml-py`
3. 验证：`nvidia-smi`

---

## 📈 节点维护

### 暂停节点（维护模式）

```bash
curl -X POST http://GATEWAY_IP:8000/api/v1/nodes/YOUR_NODE_ID/maintenance
```

### 下线节点

```bash
# 停止服务
pkill -f "agent_api.py"
pkill -f "heartbeat_client.py"

# 从集群删除
curl -X DELETE http://GATEWAY_IP:8000/api/v1/nodes/YOUR_NODE_ID
```

### 更新节点配置

```bash
# 修改 node_config.json
nano node/node_config.json

# 重启服务
pkill -f "heartbeat_client.py"
python node/heartbeat_client.py &
```

---

## 💡 最佳实践

1. **使用静态 IP**: 节点 IP 变化会导致连接中断
2. **配置 NTP**: 确保时间同步，避免心跳超时
3. **监控日志**: `tail -f logs/*.log`
4. **定期更新**: `git pull` 获取最新版本
5. **备份配置**: 备份 `node_config.json`

---

## 📞 获取帮助

- **文档**: https://github.com/chenqifu-Ai/computehub/tree/main/docs
- **Issues**: https://github.com/chenqifu-Ai/computehub/issues
- **Discord**: https://discord.gg/computehub

---

**欢迎加入 ComputeHub 算力网络！** 🎉
