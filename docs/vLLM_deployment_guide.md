# vLLM 部署完整指南

**更新时间**: 2026-04-18  
**适用版本**: vLLM 0.6.x+

---

## 📋 目录

1. [系统要求](#系统要求)
2. [安装方式](#安装方式)
3. [模型下载](#模型下载)
4. [启动服务](#启动服务)
5. [API使用](#api使用)
6. [性能优化](#性能优化)
7. [常见问题](#常见问题)

---

## 系统要求

### 硬件要求

| 组件 | 最低要求 | 推荐配置 |
|------|---------|----------|
| GPU | NVIDIA GPU, Compute 7.0+ | RTX 3090/4090, A100 |
| 显存 | 16GB (7B模型) | 24GB+ (13B+模型) |
| 内存 | 32GB | 64GB+ |
| CPU | 4核 | 8核+ |

### 软件要求

- **操作系统**: Linux (Ubuntu 20.04+)
- **Python**: 3.8 - 3.11
- **CUDA**: 11.8 - 12.1
- **PyTorch**: 2.1+

### 检查GPU

```bash
# 检查NVIDIA GPU
nvidia-smi

# 检查CUDA版本
nvcc --version

# 检查显存
nvidia-smi --query-gpu=memory.total --format=csv
```

---

## 安装方式

### 方式1: pip安装（推荐）

```bash
# 创建虚拟环境
conda create -n vllm python=3.10 -y
conda activate vllm

# 安装vLLM
pip install vllm

# 或指定版本
pip install vllm==0.6.1
```

### 方式2: 从源码安装

```bash
# 克隆仓库
git clone https://github.com/vllm-project/vllm.git
cd vllm

# 安装依赖
pip install -e .
```

### 方式3: Docker部署

```bash
# 拉取镜像
docker pull vllm/vllm-openai:latest

# 运行容器
docker run --gpus all \
  -v ~/.cache/huggingface:/root/.cache/huggingface \
  -p 8000:8000 \
  --ipc=host \
  vllm/vllm-openai:latest \
  --model meta-llama/Llama-2-7b-chat-hf
```

### 验证安装

```bash
python -c "import vllm; print(vllm.__version__)"
```

---

## 模型下载

### 方式1: Hugging Face自动下载

vLLM会自动从Hugging Face下载模型：

```bash
# 启动时指定模型名称即可
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf
```

### 方式2: 手动下载

```bash
# 使用huggingface-cli
pip install huggingface-hub

# 下载模型
huggingface-cli download meta-llama/Llama-2-7b-chat-hf \
  --local-dir /path/to/model

# 使用vLLM指定本地路径
python -m vllm.entrypoints.openai.api_server \
  --model /path/to/model
```

### 推荐模型列表

| 模型 | 参数量 | 显存需求 | 下载命令 |
|------|--------|----------|----------|
| Llama-2-7B | 7B | 16GB | `meta-llama/Llama-2-7b-chat-hf` |
| Llama-2-13B | 13B | 24GB | `meta-llama/Llama-2-13b-chat-hf` |
| Qwen-7B | 7B | 16GB | `Qwen/Qwen-7B-Chat` |
| Qwen-14B | 14B | 28GB | `Qwen/Qwen-14B-Chat` |
| Yi-6B | 6B | 14GB | `01-ai/Yi-6B-Chat` |
| DeepSeek-7B | 7B | 16GB | `deepseek-ai/deepseek-llm-7b-chat` |

---

## 启动服务

### 基础启动

```bash
# OpenAI兼容API服务器
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --host 0.0.0.0 \
  --port 8000
```

### 高级配置

```bash
# 完整参数启动
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --host 0.0.0.0 \
  --port 8000 \
  --tensor-parallel-size 1 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 4096 \
  --dtype auto \
  --trust-remote-code
```

### 参数说明

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--model` | 模型名称或路径 | 必需 |
| `--host` | 监听地址 | localhost |
| `--port` | 监听端口 | 8000 |
| `--tensor-parallel-size` | GPU并行数 | 1 |
| `--gpu-memory-utilization` | GPU显存利用率 | 0.9 |
| `--max-model-len` | 最大上下文长度 | 模型默认 |
| `--dtype` | 数据类型 | auto |
| `--trust-remote-code` | 信任远程代码 | False |

### 多GPU部署

```bash
# 2卡并行
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-13b-chat-hf \
  --tensor-parallel-size 2

# 4卡并行
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-70b-chat-hf \
  --tensor-parallel-size 4
```

---

## API使用

### OpenAI兼容API

vLLM提供完全兼容OpenAI的API接口：

#### Chat Completions

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "messages": [
      {"role": "user", "content": "Hello, how are you?"}
    ],
    "temperature": 0.7,
    "max_tokens": 100
  }'
```

#### Completions

```bash
curl http://localhost:8000/v1/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "meta-llama/Llama-2-7b-chat-hf",
    "prompt": "Once upon a time",
    "max_tokens": 50
  }'
```

#### List Models

```bash
curl http://localhost:8000/v1/models
```

### Python SDK

```python
from openai import OpenAI

# 连接vLLM服务
client = OpenAI(
    base_url="http://localhost:8000/v1",
    api_key="dummy"  # vLLM不需要API key
)

# Chat completion
response = client.chat.completions.create(
    model="meta-llama/Llama-2-7b-chat-hf",
    messages=[
        {"role": "user", "content": "解释量子力学"}
    ],
    temperature=0.7,
    max_tokens=500
)

print(response.choices[0].message.content)
```

### 流式输出

```python
# 流式生成
stream = client.chat.completions.create(
    model="meta-llama/Llama-2-7b-chat-hf",
    messages=[{"role": "user", "content": "写一首诗"}],
    stream=True
)

for chunk in stream:
    if chunk.choices[0].delta.content:
        print(chunk.choices[0].delta.content, end="")
```

---

## 性能优化

### 1. GPU显存优化

```bash
# 调整显存利用率
--gpu-memory-utilization 0.95  # 使用95%显存

# 限制上下文长度
--max-model-len 2048  # 减少上下文长度节省显存

# 使用量化模型
--load-format auto  # 自动检测量化格式
```

### 2. 批处理优化

```bash
# 最大并发请求数
--max-num-seqs 256

# 最大批处理token数
--max-num-batched-tokens 8192
```

### 3. 内核优化

```bash
# 启用CUDA内核优化
--enable-prefix-caching

# 使用FlashAttention
--attention-backend FLASHINFER
```

### 4. 量化部署

```bash
# AWQ量化模型
--model casperhansen/llama-2-7b-awq

# GPTQ量化模型
--model TheBloke/Llama-2-7B-Chat-GPTQ

# FP8量化（需要Hopper GPU）
--kv-cache-dtype fp8
```

---

## 常见问题

### 1. 显存不足

**问题**: `OutOfMemoryError: CUDA out of memory`

**解决方案**:
```bash
# 方法1: 降低显存利用率
--gpu-memory-utilization 0.85

# 方法2: 减少上下文长度
--max-model-len 2048

# 方法3: 使用量化模型
--model casperhansen/llama-2-7b-awq
```

### 2. 模型下载慢

**解决方案**:
```bash
# 设置HuggingFace镜像
export HF_ENDPOINT=https://hf-mirror.com

# 或使用ModelScope
pip install modelscope
modelscope download --model qwen/Qwen-7B-Chat
```

### 3. 多GPU不工作

**检查**:
```bash
# 检查GPU数量
python -c "import torch; print(torch.cuda.device_count())"

# 检查NCCL
python -c "import torch.distributed as dist"
```

### 4. API响应慢

**优化**:
```bash
# 启用前缀缓存
--enable-prefix-caching

# 增加并发数
--max-num-seqs 256

# 使用批处理
--max-num-batched-tokens 8192
```

---

## 部署脚本示例

### 一键部署脚本

```bash
#!/bin/bash

# vLLM一键部署脚本
# 用法: ./deploy_vllm.sh <model_name> [gpu_count]

MODEL=$1
GPU_COUNT=${2:-1}
PORT=${3:-8000}

if [ -z "$MODEL" ]; then
    echo "用法: $0 <model_name> [gpu_count] [port]"
    echo "示例: $0 meta-llama/Llama-2-7b-chat-hf 1 8000"
    exit 1
fi

echo "🚀 部署 vLLM 服务"
echo "模型: $MODEL"
echo "GPU数量: $GPU_COUNT"
echo "端口: $PORT"

# 检查GPU
if ! command -v nvidia-smi &> /dev/null; then
    echo "❌ 未检测到NVIDIA GPU"
    exit 1
fi

# 检查Python环境
if ! python -c "import vllm" 2>/dev/null; then
    echo "📦 安装 vLLM..."
    pip install vllm
fi

# 启动服务
echo "✅ 启动服务..."
python -m vllm.entrypoints.openai.api_server \
    --model "$MODEL" \
    --host 0.0.0.0 \
    --port "$PORT" \
    --tensor-parallel-size "$GPU_COUNT" \
    --gpu-memory-utilization 0.9 \
    --trust-remote-code

echo "🎉 vLLM 服务已启动在 http://localhost:$PORT"
```

### Systemd服务

```ini
# /etc/systemd/system/vllm.service
[Unit]
Description=vLLM API Server
After=network.target

[Service]
Type=simple
User=vllm
WorkingDirectory=/home/vllm
Environment="PATH=/home/vllm/miniconda3/envs/vllm/bin"
ExecStart=/home/vllm/miniconda3/envs/vllm/bin/python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --host 0.0.0.0 \
  --port 8000 \
  --gpu-memory-utilization 0.9
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl daemon-reload
sudo systemctl enable vllm
sudo systemctl start vllm

# 查看状态
sudo systemctl status vllm
```

---

## 监控和日志

### 健康检查

```bash
# 检查服务状态
curl http://localhost:8000/health

# 检查模型列表
curl http://localhost:8000/v1/models
```

### Prometheus监控

```bash
# 启用metrics端点
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --enable-metrics

# 访问metrics
curl http://localhost:8000/metrics
```

### 日志配置

```bash
# 设置日志级别
export VLLM_LOGGING_LEVEL=INFO

# 保存日志
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  > vllm.log 2>&1 &
```

---

## 对比其他方案

| 特性 | vLLM | Ollama | TGI | LMDeploy |
|------|------|--------|-----|----------|
| 性能 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| 易用性 | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐ |
| OpenAI兼容 | ✅ | ✅ | ✅ | ✅ |
| 多GPU支持 | ✅ | ❌ | ✅ | ✅ |
| 量化支持 | ✅ | ✅ | ✅ | ✅ |
| 生产就绪 | ✅ | ⭕ | ✅ | ✅ |

---

## 推荐配置

### 小规模部署（7B模型）

```bash
# 单卡RTX 3090 (24GB)
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-7b-chat-hf \
  --gpu-memory-utilization 0.9 \
  --max-model-len 4096
```

### 中规模部署（13B模型）

```bash
# 双卡RTX 3090/4090 (2x24GB)
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-13b-chat-hf \
  --tensor-parallel-size 2 \
  --gpu-memory-utilization 0.9
```

### 大规模部署（70B模型）

```bash
# 4x A100 (4x80GB)
python -m vllm.entrypoints.openai.api_server \
  --model meta-llama/Llama-2-70b-chat-hf \
  --tensor-parallel-size 4 \
  --gpu-memory-utilization 0.9 \
  --max-model-len 8192
```

---

## 总结

vLLM是生产环境部署大语言模型的优秀选择，具有：

✅ **高性能**: PagedAttention + 连续批处理  
✅ **易用性**: OpenAI兼容API  
✅ **灵活性**: 支持多种模型和硬件配置  
✅ **生产就绪**: 被广泛使用和验证  

**推荐使用场景**:
- 高并发API服务
- 多模型部署
- 生产环境推理
- 需要高吞吐量的场景

---

**文档版本**: 2026-04-18  
**参考链接**:
- 官方文档: https://vllm.readthedocs.io/
- GitHub: https://github.com/vllm-project/vllm
- 模型仓库: https://huggingface.co/models