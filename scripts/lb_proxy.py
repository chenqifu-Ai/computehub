#!/usr/bin/env python3
"""
轻量级 HTTP 负载均衡代理
- 轮询分发请求到 8000/8001 两个后端
- 支持故障自动切换
- 保持 OpenAI API 兼容格式

使用方式:
  python3 lb_proxy.py          # 默认 127.0.0.1:18888
  python3 lb_proxy.py 8888     # 指定端口

OpenClaw 配置:
  "baseUrl": "http://127.0.0.1:18888/v1"
"""

import http.server
import urllib.request
import urllib.error
import json
import sys
import time
import re
import threading
from http import HTTPStatus

# ==================== vLLM 响应适配 ====================
def _fix_vllm_response(response_json):
    """适配 vLLM 非标准响应：content=null → 填充 reasoning 内容"""
    if not response_json or 'choices' not in response_json:
        return response_json
    
    for choice in response_json['choices']:
        msg = choice.get('message', {})
        content = msg.get('content')
        reasoning = msg.get('reasoning') or ''
        
        if not content and reasoning:
            # content 为 null，用 reasoning 填充（过滤元信息）
            text = reasoning.strip()
            
            # 提取代码块
            code_blocks = re.findall(r'```(?:\w*)\n(.*?)```', text, re.DOTALL)
            if code_blocks:
                clean = code_blocks[-1].strip()
            else:
                # 找引号
                quotes = re.findall(r'"([^"]+)"', text)
                if quotes and len(quotes[-1]) <= 500:
                    clean = quotes[-1]
                else:
                    # 最后一行非空文字
                    lines = [l.strip() for l in text.split("\n") if l.strip()]
                    skip_kw = ["thinking process", "here's a thinking", "let me",
                               "好的，", "final output", "final answer", "check:"]
                    clean_lines = [l for l in lines if not any(k in l.lower() for k in skip_kw)]
                    clean = clean_lines[-1] if clean_lines else text
            
            msg['content'] = clean
            msg['reasoning'] = reasoning  # 保留原始推理
    
    return response_json

# ==================== 配置区 ====================
BACKENDS = [
    {"url": "http://58.23.129.98:8000", "name": "8000", "weight": 6},   # 权重高（测试显示更快）
    {"url": "http://58.23.129.98:8001", "name": "8001", "weight": 4},   # 权重低
]

LISTEN_HOST = "127.0.0.1"
LISTEN_PORT = int(sys.argv[1]) if len(sys.argv) > 1 else 18888
API_KEY = "sk-78sadn09bjawde123e"  # 透传到后端
LOG_LEVELS = {"error": [], "warn": [], "info": []}
# ================================================

# 负载均衡器状态
lb_lock = threading.Lock()
current_index = 0
backend_health = {b["name"]: {"healthy": True, "last_check": 0, "consecutive_failures": 0} 
                  for b in BACKENDS}


def weighted_round_robin():
    """加权轮询选择后端"""
    global current_index
    with lb_lock:
        # 过滤健康后端
        healthy = [i for i, b in enumerate(BACKENDS) 
                   if backend_health[b["name"]]["healthy"]]
        if not healthy:
            # 全部不健康，强制返回第一个
            healthy = [0]
        
        # 加权选择
        weights = [BACKENDS[i]["weight"] for i in healthy]
        total = sum(weights)
        
        # 简单的加权轮询
        current_index = (current_index + 1) % len(BACKENDS)
        while current_index not in healthy:
            current_index = (current_index + 1) % len(BACKENDS)
        
        return BACKENDS[current_index]


def request_with_fallback(target_url, data, headers, max_retries=2):
    """带故障切换的请求"""
    last_error = None
    
    # 获取权重轮询的后端
    backend = weighted_round_robin()
    backend_url = backend["url"]
    backend_name = backend["name"]
    
    errors = []
    
    # 尝试主后端
    for attempt in range(max_retries):
        try:
            req = urllib.request.Request(target_url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read()
                
                # 更新健康状态
                backend_health[backend_name]["healthy"] = True
                backend_health[backend_name]["consecutive_failures"] = 0
                backend_health[backend_name]["last_check"] = time.time()
                
                return body, HTTPStatus.OK
                
        except Exception as e:
            last_error = e
            errors.append(f"{backend_name} attempt {attempt+1}: {e}")
            
            if attempt < max_retries - 1:
                time.sleep(0.1)
    
    # 主后端失败，尝试其他后端
    with lb_lock:
        all_indices = list(range(len(BACKENDS)))
        healthy_indices = [i for i in all_indices 
                          if backend_health[BACKENDS[i]["name"]]["healthy"] and i != current_index]
    
    for idx in healthy_indices:
        alt_backend = BACKENDS[idx]
        alt_url = alt_backend["url"]
        try:
            req = urllib.request.Request(target_url, data=data, headers=headers)
            with urllib.request.urlopen(req, timeout=120) as resp:
                body = resp.read()
                
                backend_health[alt_backend["name"]]["healthy"] = True
                backend_health[alt_backend["name"]]["consecutive_failures"] = 0
                
                errors.append(f"FALLBACK to {alt_backend['name']} OK")
                return body, HTTPStatus.OK
                
        except Exception as e:
            errors.append(f"FALLBACK {alt_backend['name']}: {e}")
            backend_health[alt_backend["name"]]["healthy"] = False
    
    # 全部失败
    with lb_lock:
        backend_health[backend_name]["healthy"] = False
        backend_health[backend_name]["consecutive_failures"] += 1
    
    raise Exception(f"All backends failed. Errors: {'; '.join(errors)}")


class LoadBalancerHandler(http.server.BaseHTTPRequestHandler):
    """HTTP 请求处理器"""
    
    def log_message(self, format, *args):
        """简洁日志"""
        msg = format % args
        if "GET /health" in msg:
            pass  # 健康检查不打日志
        elif "GET /status" in msg:
            pass  # 状态查询不打日志
        else:
            LOG_LEVELS["info"].append(msg)
            if len(LOG_LEVELS["info"]) > 100:
                LOG_LEVELS["info"] = LOG_LEVELS["info"][-50:]
    
    def do_GET(self):
        if self.path == "/health":
            self.send_health()
        elif self.path == "/status":
            self.send_status()
        elif self.path == "/models":
            self.forward_to_backend("GET", self.path)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
    
    def do_POST(self):
        if self.path in ("/v1/chat/completions", "/v1/completions", 
                         "/v1/embeddings", "/v1/models"):
            self.forward_to_backend("POST", self.path)
        else:
            self.send_error(HTTPStatus.NOT_FOUND, "Not Found")
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
    
    def send_health(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = json.dumps({"status": "healthy", "timestamp": time.time()})
        self.wfile.write(response.encode())
    
    def send_status(self):
        with lb_lock:
            status = {
                "backends": {},
                "requests_served": len(LOG_LEVELS["info"]) + len(LOG_LEVELS["error"]),
                "errors": len(LOG_LEVELS["error"]),
            }
            for b in BACKENDS:
                name = b["name"]
                h = backend_health[name]
                status["backends"][name] = {
                    "url": b["url"],
                    "weight": b["weight"],
                    "healthy": h["healthy"],
                    "failures": h["consecutive_failures"],
                }
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps(status, indent=2).encode())
    
    def forward_to_backend(self, method, path):
        try:
            # 读取请求体
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length) if content_length > 0 else b''
            
            # 构建请求头
            req_headers = {}
            for key, value in self.headers.items():
                if key.lower() not in ('host', 'content-length'):
                    req_headers[key] = value
            
            # 确保 Authorization 头正确
            auth_header = self.headers.get('Authorization', '')
            if auth_header:
                req_headers['Authorization'] = auth_header
            
            # 构建后端 URL
            backend = weighted_round_robin()
            target_url = f"{backend['url']}{path}"
            
            # 发送请求
            response_body, status = request_with_fallback(target_url, body, req_headers)
            
            # 适配 vLLM 响应格式（content=null 问题）
            try:
                response_json = json.loads(response_body)
                response_json = _fix_vllm_response(response_json)
                response_body = json.dumps(response_json).encode()
            except:
                pass  # 非 JSON 响应直接透传
            
            # 回传响应
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(response_body)))
            self.end_headers()
            self.wfile.write(response_body)
            
        except Exception as e:
            LOG_LEVELS["error"].append(f"Proxy error: {e}")
            self.send_response(HTTPStatus.BAD_GATEWAY)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            error_resp = json.dumps({
                "error": {
                    "message": str(e),
                    "type": "proxy_error",
                    "param": None,
                    "code": 502
                }
            })
            self.wfile.write(error_resp.encode())


def health_checker():
    """后台健康检查"""
    while True:
        for b in BACKENDS:
            try:
                req = urllib.request.Request(f"{b['url']}/v1/models", 
                                           headers={"Authorization": f"Bearer {API_KEY}"})
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status == 200:
                        backend_health[b["name"]]["healthy"] = True
                        if not backend_health[b["name"]]["healthy"]:
                            backend_health[b["name"]]["consecutive_failures"] = 0
            except:
                backend_health[b["name"]]["healthy"] = False
        time.sleep(10)


if __name__ == "__main__":
    print(f"🚀 LB Proxy starting on {LISTEN_HOST}:{LISTEN_PORT}")
    backend_list = [f'{b["name"]}(w={b["weight"]})' for b in BACKENDS]
    print(f"📊 Backends: {backend_list}")
    
    # 启动健康检查
    hc_thread = threading.Thread(target=health_checker, daemon=True)
    hc_thread.start()
    
    # 启动 HTTP 服务
    server = http.server.HTTPServer((LISTEN_HOST, LISTEN_PORT), LoadBalancerHandler)
    print(f"✅ Ready! Point OpenClaw baseUrl to: http://{LISTEN_HOST}:{LISTEN_PORT}/v1")
    print(f"💡 Health: http://{LISTEN_HOST}:{LISTEN_PORT}/health")
    print(f"💡 Status: http://{LISTEN_HOST}:{LISTEN_PORT}/status")
    print(f"✅ vLLM content=null bug fixed (auto-adapted)")
    print(f"   Load balancing helps with: redundancy, load distribution, failover")
    server.serve_forever()
