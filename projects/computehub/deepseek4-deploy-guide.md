# DeepSeek4 + ComputeHub 部署方案

## 方案 A：Ollama（最简单 ✅）

```bash
# 1. 安装 Ollama
curl -fsSL https://ollama.com/install.sh | sh

# 2. 拉取 DeepSeek4 模型
ollama pull deepseek-r1:671b

# 3. 启动服务（默认端口 11434）
ollama serve

# 4. 验证
curl http://localhost:11434/api/generate -d '{"model":"deepseek-r1","prompt":"hello","stream":false}'
```

### ComputeHub 对接 Ollama

```json
// config.json
{
  "provider": "ollama",
  "endpoint": "http://localhost:11434",
  "model": "deepseek-r1:671b",
  "max_concurrent": 4
}
```

---

## 方案 B：vLLM（生产级，高性能 ✅✅）

```bash
# 1. 安装 vLLM
pip install vllm

# 2. 启动 DeepSeek4 推理服务
python -m vllm.entrypoints.api_server \
  --model deepseek-ai/DeepSeek-R1-Distill-Llama-70B \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 4  # 多卡并行

# 3. 验证
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-r1","messages":[{"role":"user","content":"hello"}]}'
```

### ComputeHub 对接 vLLM

```json
{
  "provider": "openai-compatible",
  "endpoint": "http://gpu-node1:8000/v1",
  "api_key": "optional",
  "max_concurrent": 16
}
```

---

## 方案 C：OpenClaw 现有配置（最省事 ✅✅✅）

老大你已经配置好了 NewAPI：
```
地址: https://ai.zhangtuokeji.top:9090/v1
模型: qwen3.6-35b-common
Key: sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl
```

**ComputeHub 直接对接现有 API 即可**，不需要自己部署模型。

---

## 五、生产环境部署

### 最小可行部署（MVP）

```
┌─────────────────────────────────────┐
│  一台 GPU 服务器 (24GB+ VRAM)        │
│                                     │
│  ├── Ollama (DeepSeek4)             │
│  ├── ComputeHub Gateway             │
│  ├── 数据库 (PostgreSQL/Redis)       │
│  └── TUI 管理界面                   │
└─────────────────────────────────────┘
```

### 扩展部署（多节点）

```
                    ┌──────────────┐
                    │  用户请求      │
                    └──────┬───────┘
                           │
              ┌────────────▼────────────┐
              │   ComputeHub Gateway    │  ← 独立服务器
              │   (负载均衡 + 路由)       │
              └────┬──────────┬─────────┘
                   │          │
            ┌──────▼───┐  ┌──▼──────────┐
            │GPU节点-1  │  │GPU节点-2    │
            │ Ollama    │  │ Ollama      │
            │ + vLLM    │  │ + vLLM      │
            └────────────┘  └────────────┘
```

### 成本估算

| 方案 | GPU | 月成本 | 适用场景 |
|------|-----|--------|---------|
| MVP | 1x A10 (24GB) | ~¥500 | 内部测试/小团队 |
| 生产 | 2x A100 (80GB) | ~¥4000 | 企业级服务 |
| 高性能 | 4x H100 (80GB) | ~¥12000 | 高并发生产 |

---

## 六、关键决策

**现在最合理的路线：**

1. **先用 NewAPI（你现有的）** — 零成本验证 ComputeHub 调度逻辑
2. **Ollama 本地部署** — 等有新服务器时，DeepSeek4 跑在本地
3. **vLLM 生产部署** — 规模扩大时，从 Ollama 升级到 vLLM

**不需要 DeepSeek4 支持"分布式算力"** — 它只负责推理，调度是 ComputeHub 的事。
