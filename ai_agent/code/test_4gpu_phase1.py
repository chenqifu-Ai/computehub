#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
4 卡 GPU 测试计划 - 阶段 1：硬件确认
"""
import requests, json, time

API_URL = "http://58.23.129.98:8001/v1/chat/completions"
HEADERS = {"Content-Type": "application/json", "Authorization": "Bearer sk-78sadn09bjawde123e"}

def test_gpu_info():
    """获取 GPU 硬件信息"""
    print("=" * 80)
    print("  🧪 阶段 1：硬件确认")
    print("=" * 80)
    
    # 请求 AI 执行硬件检测代码
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [{"type": "text", "text": """请执行以下 Python 代码并返回完整输出结果：

```python
import os
print("=" * 60)
print("=== NVIDIA GPU 信息 ===")
print("=" * 60)
os.system('nvidia-smi -q')

print("\n" + "=" * 60)
print("=== GPU 拓扑 ===")
print("=" * 60)
os.system('nvidia-smi topo -m')

print("\n" + "=" * 60)
print("=== PyTorch CUDA 信息 ===")
print("=" * 60)
try:
    import torch
    print(f"CUDA 可用: {torch.cuda.is_available()}")
    print(f"CUDA 版本: {torch.version.cuda}")
    print(f"GPU 数量: {torch.cuda.device_count()}")
    
    for i in range(torch.cuda.device_count()):
        props = torch.cuda.get_device_properties(i)
        print(f"\nGPU {i}:")
        print(f"  型号: {props.name}")
        print(f"  显存: {props.total_mem / 1e9:.0f}GB ({props.total_mem / (1024**3):.0f}GB)")
        print(f"  计算能力: {props.major}.{props.minor}")
        print(f"  CUDA 核心数: {props.multi_processor_count} SMs")
        
except Exception as e:
    print(f"PyTorch 错误: {e}")

print("\n" + "=" * 60)
print("=== 系统信息 ===")
print("=" * 60)
try:
    import psutil
    vm = psutil.virtual_memory()
    print(f"系统总内存: {vm.total / 1e9:.1f}GB")
    print(f"系统已用内存: {vm.used / 1e9:.1f}GB")
    print(f"系统可用内存: {vm.available / 1e9:.1f}GB")
except Exception as e:
    print(f"psutil 错误: {e}")

try:
    import subprocess
    result = subprocess.run(['lscpu'], capture_output=True, text=True, timeout=10)
    for line in result.stdout.split('\n'):
        if 'Model name' in line or 'CPU(s):' in line or 'Thread' in line or 'Core' in line:
            print(line)
except Exception as e:
    print(f"lscpu 错误: {e}")

print("\n" + "=" * 60)
print("=== 系统资源使用 ===")
print("=" * 60)
try:
    os.system('free -h')
    os.system('df -h /')
except Exception as e:
    print(f"系统命令错误: {e}")
"""}]}],
        "max_tokens": 5000,
        "temperature": 0.3
    }
    
    start = time.time()
    r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=120)
    elapsed = time.time() - start
    
    if r.status_code == 200:
        data = r.json()
        choice = data.get('choices', [{}])[0]
        message = choice.get('message', {})
        reasoning = message.get('reasoning', '')
        content = message.get('content', '')
        
        print(f"\n✅ 硬件探测请求完成")
        print(f"  耗时：{elapsed:.2f}s")
        print(f"  响应长度：{len(reasoning) + len(content)} 字符")
        print(f"\n📋 硬件信息：")
        print("-" * 80)
        
        # 优先使用 reasoning 字段
        response_text = reasoning or content
        if response_text:
            # 过滤掉思考过程，保留实际代码输出
            lines = response_text.split('\n')
            in_code_block = False
            code_output = []
            
            for line in lines:
                if '```' in line:
                    in_code_block = not in_code_block
                    continue
                if in_code_block:
                    code_output.append(line)
                elif '=' in line and ('GPU' in line or '系统' in line or 'PyTorch' in line):
                    code_output.append(line)
                elif any(keyword in line for keyword in ['GPU_COUNT', 'GPU0:', 'GPU1:', 'GPU2:', 'GPU3:', 'VRAM:', '型号:', '显存:', '总内存:', '已用:', '可用:', 'NVIDIA']):
                    code_output.append(line)
            
            print('\n'.join(code_output[:200]))  # 限制输出长度
        else:
            print("  ⚠️ 未获取到有效硬件信息")
    else:
        print(f"❌ HTTP {r.status_code}")
    
    return elapsed

def test_api_info():
    """获取 API 元信息"""
    print("\n" + "=" * 80)
    print("  📡 API 元信息查询")
    print("=" * 80)
    
    # 测试模型信息
    payload = {
        "model": "qwen3.6-35b",
        "messages": [{"role": "user", "content": [{"type": "text", "text": "你运行的环境是什么？请告诉我 GPU 数量、型号、显存大小、tensor_parallel_size 配置。"}]}],
        "max_tokens": 500
    }
    
    start = time.time()
    r = requests.post(API_URL, json=payload, headers=HEADERS, timeout=60)
    elapsed = time.time() - start
    
    if r.status_code == 200:
        data = r.json()
        usage = data.get('usage', {})
        choice = data.get('choices', [{}])[0]
        message = choice.get('message', {})
        reasoning = message.get('reasoning', '')
        content = message.get('content', '')
        
        print(f"\n✅ API 查询完成")
        print(f"  耗时：{elapsed:.2f}s")
        print(f"  总 tokens：{usage.get('total_tokens', '?')}")
        print(f"\n📋 AI 回答：")
        print("-" * 80)
        
        response_text = reasoning or content
        if response_text:
            # 提取关键信息
            print(response_text[:1000])
        else:
            print("  ⚠️ 未获取到有效信息")
    else:
        print(f"❌ HTTP {r.status_code}")

def main():
    print("\n🚀 开始执行阶段 1：硬件确认\n")
    
    test_gpu_info()
    test_api_info()
    
    print("\n" + "=" * 80)
    print("  ✅ 阶段 1 完成")
    print("=" * 80)

if __name__ == "__main__":
    main()
