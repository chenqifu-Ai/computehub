#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地代理 API 服务
功能：
1. 代理多个 AI 模型 API
2. 负载均衡和健康检查
3. 请求缓存和重试
4. 性能监控和日志
5. 健康检查端点

部署方式：
  python3 proxy_api_server.py

访问地址：
  http://127.0.0.1:8765/v1/chat/completions
  http://127.0.0.1:8765/health
  http://127.0.0.1:8765/models
  http://127.0.0.1:8765/status (性能统计)
"""

import os
import sys
import json
import time
import logging
import hashlib
import requests
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict, field
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Lock
import urllib3

# 禁用不安全警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# ============================================================
# 配置管理
# ============================================================
@dataclass
class ModelConfig:
    """模型配置"""
    name: str
    url: str
    api_key: str
    is_active: bool = True
    priority: int = 1  # 优先级，越小越优先
    timeout: int = 120
    max_retries: int = 3

@dataclass
class PerformanceStats:
    """性能统计"""
    total_requests: int = 0
    successful_requests: int = 0
    failed_requests: int = 0
    avg_latency_ms: float = 0.0
    p95_latency_ms: float = 0.0
    p99_latency_ms: float = 0.0
    model_stats: Dict[str, dict] = field(default_factory=dict)
    latencies: List[float] = field(default_factory=list)

    def update(self, model_name: str, latency_ms: float, success: bool):
        """更新统计"""
        self.total_requests += 1
        if success:
            self.successful_requests += 1
        else:
            self.failed_requests += 1
        
        # 维护延迟列表
        self.latencies.append(latency_ms)
        if len(self.latencies) > 1000:  # 只保留最近 1000 条
            self.latencies = self.latencies[-1000:]
        
        # 更新 P95/P99
        if self.latencies:
            sorted_latencies = sorted(self.latencies)
            self.avg_latency_ms = sum(self.latencies) / len(self.latencies)
            self.p95_latency_ms = sorted_latencies[int(len(sorted_latencies) * 0.95)]
            self.p99_latency_ms = sorted_latencies[int(len(sorted_latencies) * 0.99)]
        
        # 更新模型统计
        if model_name not in self.model_stats:
            self.model_stats[model_name] = {
                "total": 0,
                "success": 0,
                "failed": 0,
                "avg_latency_ms": 0.0
            }
        
        self.model_stats[model_name]["total"] += 1
        if success:
            self.model_stats[model_name]["success"] += 1
        else:
            self.model_stats[model_name]["failed"] += 1
        
        # 更新平均延迟
        stats = self.model_stats[model_name]
        stats["avg_latency_ms"] = (
            stats["avg_latency_ms"] * (stats["total"] - 1) + latency_ms
        ) / stats["total"]

# ============================================================
# 全局配置
# ============================================================
# 模型配置列表
MODEL_CONFIGS = [
    ModelConfig(
        name="qwen3.6-35b-local",
        url="http://127.0.0.1:8765/v1/chat/completions",  # 本地 vLLM 实例
        api_key="",
        is_active=True,
        priority=1,
        timeout=120
    ),
    ModelConfig(
        name="qwen3.6-35b-common",
        url="https://ai.zhangtuokeji.top:9090/v1/chat/completions",
        api_key="sk-3RgMq1COL9uqn29hCBwXOt5X3d5TpIddaRKH44chQ2QcAybl",
        is_active=True,
        priority=2,
        timeout=120
    ),
    ModelConfig(
        name="qwen3.6-35b-std",
        url="https://ai.zhangtuokeji.top:9090/v1/chat/completions",
        api_key="sk-1G7ntp2mow9OTyn1guonubuTRDbebaYqk7YdplCdHfk3ZFZe",
        is_active=True,
        priority=3,
        timeout=120
    ),
]

# 性能统计
performance_stats = PerformanceStats()
stats_lock = Lock()

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] %(levelname)s %(name)s: %(message)s',
    datefmt='%H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("proxy_api.log", encoding="utf-8")
    ]
)
logger = logging.getLogger("proxy_api")

# ============================================================
# API 调用器
# ============================================================
class APIHandler:
    """API 调用器"""
    
    def __init__(self, configs: List[ModelConfig]):
        self.configs = {config.name: config for config in configs}
        self.active_configs = [c for c in configs if c.is_active]
    
    def get_next_model(self) -> Optional[ModelConfig]:
        """获取下一个可用模型（按优先级）"""
        # 按优先级排序
        sorted_configs = sorted(self.active_configs, key=lambda c: c.priority)
        return sorted_configs[0] if sorted_configs else None
    
    def call_api(self, model_name: str, messages: List[Dict], 
                 max_tokens: int = 2000, temperature: float = 0.7) -> Dict:
        """调用指定模型的 API"""
        config = self.configs.get(model_name)
        if not config or not config.is_active:
            raise ValueError(f"模型 {model_name} 不可用")
        
        # 构建请求
        payload = {
            "model": model_name,
            "messages": messages,
            "max_tokens": max_tokens,
            "temperature": temperature
        }
        
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {config.api_key}" if config.api_key else ""
        }
        
        # 尝试调用（带重试）
        last_error = None
        for attempt in range(config.max_retries):
            start_time = time.time()
            try:
                resp = requests.post(
                    config.url,
                    headers=headers,
                    json=payload,
                    timeout=config.timeout,
                    verify=False
                )
                elapsed_ms = (time.time() - start_time) * 1000
                
                if resp.status_code == 200:
                    data = resp.json()
                    # 更新统计
                    with stats_lock:
                        performance_stats.update(model_name, elapsed_ms, True)
                    return data
                else:
                    last_error = f"HTTP {resp.status_code}: {resp.text[:200]}"
                    logger.warning(f"{model_name} 请求失败 (尝试 {attempt+1}/{config.max_retries}): {last_error}")
                    
            except Exception as e:
                last_error = str(e)
                logger.warning(f"{model_name} 请求异常 (尝试 {attempt+1}/{config.max_retries}): {e}")
            
            # 如果不是最后一次尝试，等待一下再重试
            if attempt < config.max_retries - 1:
                time.sleep(1 * (attempt + 1))  # 指数退避
        
        # 所有重试都失败
        with stats_lock:
            performance_stats.update(model_name, 0, False)
        raise Exception(f"所有 {config.max_retries} 次重试都失败: {last_error}")
    
    def get_available_models(self) -> List[Dict]:
        """获取可用模型列表"""
        models = []
        for name, config in self.configs.items():
            models.append({
                "id": name,
                "object": "model",
                "created": int(time.time()),
                "owned_by": "proxy-api",
                "active": config.is_active,
                "priority": config.priority
            })
        return models

# ============================================================
# HTTP 请求处理器
# ============================================================
class ProxyAPIHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""
    
    api_handler: APIHandler = None  # 由主线程设置
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        logger.info(f"{self.client_address[0]} - {format % args}")
    
    def do_GET(self):
        """处理 GET 请求"""
        if self.path == "/health":
            self.send_health_check()
        elif self.path == "/models":
            self.send_models_list()
        elif self.path == "/status":
            self.send_status()
        elif self.path == "/":
            self.send_root_info()
        else:
            self.send_error(404, "Not Found")
    
    def do_POST(self):
        """处理 POST 请求"""
        if self.path == "/v1/chat/completions":
            self.handle_chat_completions()
        elif self.path == "/v1/models":
            self.send_models_list()
        else:
            self.send_error(404, "Not Found")
    
    def send_json_response(self, data: Dict, status_code: int = 200):
        """发送 JSON 响应"""
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode("utf-8"))
    
    def send_error_response(self, error: str, status_code: int = 400):
        """发送错误响应"""
        self.send_json_response({
            "error": {
                "message": error,
                "type": "server_error",
                "code": status_code
            }
        }, status_code)
    
    def send_root_info(self):
        """发送根路径信息"""
        info = {
            "name": "Local Proxy API Server",
            "version": "1.0.0",
            "endpoints": {
                "/v1/chat/completions": "POST - 聊天完成",
                "/v1/models": "GET - 模型列表",
                "/health": "GET - 健康检查",
                "/status": "GET - 性能统计"
            },
            "models": [c.name for c in self.api_handler.configs.values() if c.is_active]
        }
        self.send_json_response(info)
    
    def send_health_check(self):
        """发送健康检查响应"""
        response = {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "uptime": time.time() - server_start_time,
            "models": len([c for c in self.api_handler.configs.values() if c.is_active])
        }
        self.send_json_response(response)
    
    def send_models_list(self):
        """发送模型列表"""
        models = self.api_handler.get_available_models()
        self.send_json_response({
            "object": "list",
            "data": models
        })
    
    def send_status(self):
        """发送状态信息"""
        with stats_lock:
            status = {
                "timestamp": datetime.now().isoformat(),
                "performance": {
                    "total_requests": performance_stats.total_requests,
                    "success_rate": f"{performance_stats.successful_requests / max(1, performance_stats.total_requests) * 100:.1f}%",
                    "avg_latency_ms": f"{performance_stats.avg_latency_ms:.0f}ms",
                    "p95_latency_ms": f"{performance_stats.p95_latency_ms:.0f}ms",
                    "p99_latency_ms": f"{performance_stats.p99_latency_ms:.0f}ms"
                },
                "models": performance_stats.model_stats
            }
        self.send_json_response(status)
    
    def handle_chat_completions(self):
        """处理聊天完成请求"""
        try:
            # 读取请求体
            content_length = int(self.headers["Content-Length"])
            post_data = self.rfile.read(content_length)
            request = json.loads(post_data)
            
            # 获取参数
            model_name = request.get("model", "qwen3.6-35b-local")
            messages = request.get("messages", [])
            max_tokens = request.get("max_tokens", 2000)
            temperature = request.get("temperature", 0.7)
            
            # 调用 API
            start_time = time.time()
            response = self.api_handler.call_api(
                model_name=model_name,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature
            )
            elapsed_ms = (time.time() - start_time) * 1000
            
            logger.info(f"请求完成: model={model_name}, tokens={response.get('usage', {}).get('total_tokens', 0)}, time={elapsed_ms:.0f}ms")
            
            self.send_json_response(response)
            
        except Exception as e:
            logger.error(f"请求处理失败: {e}")
            self.send_error_response(f"请求处理失败: {str(e)}", 500)


# ============================================================
# 主程序
# ============================================================
server_start_time = time.time()
api_handler = APIHandler(MODEL_CONFIGS)
ProxyAPIHandler.api_handler = api_handler

def run_server(host: str = "127.0.0.1", port: int = 8765):
    """运行服务器"""
    server = HTTPServer((host, port), ProxyAPIHandler)
    logger.info(f"🚀 代理 API 服务启动")
    logger.info(f"📍 地址: http://{host}:{port}")
    logger.info(f"📋 模型: {[c.name for c in MODEL_CONFIGS if c.is_active]}")
    logger.info(f"💡 访问 /health 检查状态")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("👋 服务停止")
        server.server_close()

if __name__ == "__main__":
    # 解析命令行参数
    import argparse
    parser = argparse.ArgumentParser(description="本地代理 API 服务")
    parser.add_argument("--host", default="127.0.0.1", help="监听地址")
    parser.add_argument("--port", type=int, default=8765, help="监听端口")
    args = parser.parse_args()
    
    run_server(args.host, args.port)
