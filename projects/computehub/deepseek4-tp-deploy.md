# DeepSeek4 多卡分布式推理部署指南

## 环境要求

| 项目 | 要求 |
|------|------|
| GPU | 2-8 张 NVIDIA 显卡（推荐同型号） |
| 显存 | 单卡至少 16GB，4卡合计 ≥ 80GB |
| 互联 | NVLink/NVSwitch 最好，PCIe 也行 |
| 系统 | Ubuntu 20.04+ / CentOS 7+ |
| Python | 3.10+ |

## 🚀 部署步骤

### 第1步：安装基础环境

```bash
# 1. 检查显卡
nvidia-smi

# 2. 安装 CUDA（如果缺失）
wget https://developer.download.nvidia.com/compute/cuda/12.4.0/local_installers/cuda_12.4.0_550.54.14_linux.run
sudo sh cuda_12.4.0_550.54.14_linux.run

# 3. 安装 Python 环境
sudo apt update && sudo apt install python3-pip python3-venv git -y

# 4. 创建虚拟环境
python3 -m venv deepseek-env
source deepseek-env/bin/activate
```

### 第2步：安装 vLLM

```bash
# 方法一：pip 安装（推荐）
pip install vllm

# 方法二：源码安装（需要更多依赖）
# git clone https://github.com/vllm-project/vllm.git
# cd vllm
# pip install -e .
```

### 第3步：下载 DeepSeek4 模型权重

```bash
# 方法一：HuggingFace 下载（需要网络）
pip install huggingface-hub
huggingface-cli download deepseek-ai/DeepSeek-R1-Distill-Llama-70B \
  --local-dir ./models/DeepSeek-R1-Distill-Llama-70B

# 方法二：已有模型文件（拷贝到 models/ 目录下即可）
# ls -la ./models/DeepSeek-R1-70B/
```

### 第4步：启动分布式推理服务

#### 4.1 单节点多卡（最常用）

```bash
# 4卡 Tensor Parallelism（4xA10 24GB 或 2xA100 80GB）
python -m vllm.entrypoints.openai.api_server \
  --model ./models/DeepSeek-R1-Distill-Llama-70B \
  --tensor-parallel-size 4 \
  --dtype bfloat16 \
  --gpu-memory-utilization 0.95 \
  --max-model-len 8192 \
  --host 0.0.0.0 \
  --port 8000
```

**参数含义：**
- `--tensor-parallel-size 4`：4张卡并行推理（核心关键！）
- `--dtype bfloat16`：半精度，显存减半
- `--gpu-memory-utilization 0.95`：显存利用率95%

#### 4.2 Int8 量化（显存不够时用，速度稍慢但省一半显存）

```bash
python -m vllm.entrypoints.openai.api_server \
  --model ./models/DeepSeek-R1-Distill-Llama-70B \
  --tensor-parallel-size 4 \
  --quantization bitsandbytes \
  --dtype float16 \
  --gpu-memory-utilization 0.9 \
  --host 0.0.0.0 \
  --port 8000
```

#### 4.3 验证服务

```bash
# 测试推理
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "DeepSeek-R1-Distill-Llama-70B",
    "messages": [{"role": "user", "content": "你好，请介绍一下你自己"}],
    "max_tokens": 512,
    "temperature": 0.7
  }'
# 返回约 3-10 秒（取决于显卡）
```

### 第5步：ComputeHub 对接

```bash
# 配置文件（compute-hub/config.json）
{
  "deployment_name": "deepseek4-cluster",
  "providers": [
    {
      "name": "deepseek4-tp4",
      "type": "openai-compatible",
      "base_url": "http://localhost:8000/v1",
      "api_key": "not-needed",
      "models": ["DeepSeek-R1-Distill-Llama-70B"],
      "max_concurrent": 8
    }
  ],
  "multi_tenant": {
    "enabled": true,
    "default_quota_tokens_per_day": 100000,
    "rate_limit_enabled": true,
    "rate_limit_rpm": 60
  },
  "cache": {
    "enabled": true,
    "backend": "redis",
    "redis_url": "redis://localhost:6379/0",
    "ttl_seconds": 3600,
    "semantic_cache_enabled": true
  },
  "billing": {
    "enabled": true,
    "per_token_cost": 0.000003
  }
}
```

## 📊 显存估算

| 配置 | 显存需求 | 推荐显卡 | 价格/月 |
|------|---------|---------|---------|
| FP16 完整精度 | ~140GB | 2x A100 80G | ~¥24,000 |
| BF16 半精度 | ~70GB | 4x A10 24G | ~¥7,200 |
| Int8 量化 | ~35GB | 2x A10 24G | ~¥3,600 |
| Int4 量化 | ~18GB | 1x A100 80G | ~¥12,000 |

> **小B推荐**：4x A10 24GB + Int8 量化 = ￥1,800/人/月（按4人拼）

## ⚠️ 常见问题

### Q: 显存不够怎么办？
```bash
# 1. 用 Int8 量化（显存减半）
# 2. 减少 max-model-len（默认 4096 → 2048）
# 3. 减少 gpu-memory-utilization（0.95 → 0.8）
python -m vllm.entrypoints.openai.api_server \
  --model ./models/DeepSeek-R1-70B \
  --tensor-parallel-size 4 \
  --quantization bitsandbytes \
  --max-model-len 2048 \
  --gpu-memory-utilization 0.8
```

### Q: 不同型号显卡能混用吗？
```bash
# 可以，但会有木桶效应（以最慢卡的速度运行）
# 推荐同型号，实在要混用：
# 将同一型号卡分到一组 tensor_parallel
```

### Q: 速度太慢怎么办？
```bash
# 1. 减少 tensor-parallel-size（2卡比4卡通信开销小）
# 2. 确保卡间用 NVLink（不要走 PCIe）
# 3. 增加 batch size
nvidia-smi topo -m  # 查看卡间互联拓扑
```

## 🏗️ 多节点分布式（跨机器）

如果需要跨多台机器（比如多个小B的 GPU 分布在不同服务器）：

```bash
# 节点1（主节点）
python -m vllm.entrypoints.openai.api_server \
  --model ./models/DeepSeek-R1-70B \
  --tensor-parallel-size 4 \
  --pipeline-parallel-size 2 \
  --distributed-executor-backend ray \
  --host 0.0.0.0 --port 8000

# 节点2（子节点）
python -m vllm.entrypoints.openai.api_server \
  --model ./models/DeepSeek-R1-70B \
  --tensor-parallel-size 4 \
  --pipeline-parallel-size 2 \
  --distributed-executor-backend ray \
  --host 0.0.0.0 --port 8001
```

> ⚠️ **跨节点部署网络延迟高，尽量放同一个机房**

## ✅ 部署检查清单

- [ ] `nvidia-smi` 显卡正常
- [ ] pip 安装 vllm 成功
- [ ] 模型权重下载完毕
- [ ] 4卡 TP 启动无报错
- [ ] curl 测试推理正常
- [ ] ComputeHub 配置完成
- [ ] 多租户功能验证
