#!/usr/bin/env python3
"""
Ollama Token 拦截代理服务器
原理：拦截 Ollama API 请求和响应，提取 prompt_tokens 和 completion_tokens
用法：python3 scripts/ollama-token-proxy.py
监听：http://127.0.0.1:8181 (代理到 11434)
"""

import http.proxy
import json
import os
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
import urllib.request
import urllib.error

# 配置
OLLAMA_HOST = "127.0.0.1"
OLLAMA_PORT = 11434
PROXY_PORT = 8181
LOG_DIR = "/root/.openclaw/workspace/logs/ollama-token"

# 创建日志目录
os.makedirs(LOG_DIR, exist_ok=True)

SUMMARY_FILE = os.path.join(LOG_DIR, "summary.txt")
DETAILED_FILE = os.path.join(LOG_DIR, "detailed.log")
REQUESTS_LOG = os.path.join(LOG_DIR, "requests.log")

# 统计数据
stats = {
    "total_requests": 0,
    "total_prompt_tokens": 0,
    "total_completion_tokens": 0,
    "total_tokens": 0,
    "requests": []
}


def log_request(endpoint, method, status, prompt_tokens, completion_tokens, model):
    """记录单次请求的 token 使用"""
    stats["total_requests"] += 1
    stats["total_prompt_tokens"] += prompt_tokens
    stats["total_completion_tokens"] += completion_tokens
    stats["total_tokens"] += (prompt_tokens + completion_tokens)

    request_info = {
        "timestamp": datetime.now().isoformat(),
        "endpoint": endpoint,
        "method": method,
        "status": status,
        "model": model,
        "prompt_tokens": prompt_tokens,
        "completion_tokens": completion_tokens,
        "total_tokens": prompt_tokens + completion_tokens
    }
    stats["requests"].append(request_info)

    # 写入请求日志
    with open(REQUESTS_LOG, "a") as f:
        f.write(f"{request_info['timestamp']} | {model:20s} | "
                f"prompt: {prompt_tokens:6d} | completion: {completion_tokens:6d} | "
                f"total: {prompt_tokens + completion_tokens:8d} | {endpoint}\n")


def write_summary():
    """写入简要日志"""
    with open(SUMMARY_FILE, "w") as f:
        f.write(f"{'='*60}\n")
        f.write(f"Ollama Token 监控 - 简要摘要\n")
        f.write(f"更新时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"{'='*60}\n\n")

        f.write("📊 统计概览\n")
        f.write(f"   总请求数：{stats['total_requests']}\n")
        f.write(f"   总输入 tokens：{stats['total_prompt_tokens']:,}\n")
        f.write(f"   总输出 tokens：{stats['total_completion_tokens']:,}\n")
        f.write(f"   总 tokens：{stats['total_tokens']:,}\n\n")

        if stats["total_tokens"] > 0:
            f.write("📈 平均每次请求\n")
            f.write(f"   输入 tokens：{stats['total_prompt_tokens'] / stats['total_requests']:.0f}\n")
            f.write(f"   输出 tokens：{stats['total_completion_tokens'] / stats['total_requests']:.0f}\n")
            f.write(f"   总 tokens：{stats['total_tokens'] / stats['total_requests']:.0f}\n\n")

        f.write("🔥 最近 10 次请求\n")
        for req in stats["requests"][-10:][::-1]:
            f.write(f"   {req['timestamp'][:19]} | {req['model']:20s} | "
                    f"↓{req['prompt_tokens']:5d} ↑{req['completion_tokens']:5d} | {req['endpoint']}\n")


def write_detailed():
    """写入详细日志"""
    with open(DETAILED_FILE, "a") as f:
        f.write(f"\n\n{'='*80}\n")
        f.write(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] Token 使用记录\n")
        f.write(f"{'='*80}\n\n")

        for req in stats["requests"][-1:]:
            f.write(f"请求 ID: {len(stats['requests'])}\n")
            f.write(f"  时间：{req['timestamp']}\n")
            f.write(f"  模型：{req['model']}\n")
            f.write(f"  接口：{req['method']} {req['endpoint']}\n")
            f.write(f"  状态：{req['status']}\n")
            f.write(f"  输入 tokens：{req['prompt_tokens']}\n")
            f.write(f"  输出 tokens：{req['completion_tokens']}\n")
            f.write(f"  总 tokens：{req['total_tokens']}\n\n")


class OllamaProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        """处理 GET 请求"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        try:
            # 代理请求到 Ollama
            url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}{path}"
            req = urllib.request.Request(url)
            response = urllib.request.urlopen(req, timeout=30)

            # 读取响应
            response_data = response.read()

            # 写入响应
            self.send_response(response.status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(response_data))
            self.end_headers()
            self.wfile.write(response_data)

            # 记录简要信息
            if path == "/api/tags":
                log_request(path, "GET", response.status, 0, 0, "-")

        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(str(e).encode())

    def do_POST(self):
        """处理 POST 请求，提取 token 信息"""
        parsed_path = urlparse(self.path)
        path = parsed_path.path

        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        request_body = self.rfile.read(content_length)

        try:
            # 代理请求到 Ollama
            url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}{path}"
            req = urllib.request.Request(url, data=request_body, method='POST')
            req.add_header('Content-Type', 'application/json')

            response = urllib.request.urlopen(req, timeout=300)

            # 读取响应
            response_data = response.read()
            response_json = json.loads(response_data.decode())

            # 提取 token 信息
            prompt_tokens = response_json.get('prompt_eval_count', 0)
            completion_tokens = response_json.get('eval_count', 0)
            model = response_json.get('model', 'unknown')

            # 记录 token 使用
            log_request(path, "POST", response.status, prompt_tokens, completion_tokens, model)

            # 写入日志文件
            write_summary()
            write_detailed()

            # 写入响应
            self.send_response(response.status)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(response_data))
            self.end_headers()
            self.wfile.write(response_data)

        except urllib.error.HTTPError as e:
            # 错误请求也代理
            response_data = e.read()
            self.send_response(e.code)
            self.send_header('Content-Type', 'application/json')
            self.send_header('Content-Length', len(response_data))
            self.end_headers()
            self.wfile.write(response_data)
        except Exception as e:
            self.send_response(502)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(f"Proxy error: {str(e)}".encode())

    def log_message(self, format, *args):
        """抑制默认日志输出"""
        pass


def print_status():
    """打印当前状态"""
    print(f"\n{'='*60}")
    print(f"Ollama Token 代理服务器已启动")
    print(f"{'='*60}")
    print(f"\n📊 统计信息：")
    print(f"   总请求数：{stats['total_requests']}")
    print(f"   总输入 tokens：{stats['total_prompt_tokens']:,}")
    print(f"   总输出 tokens：{stats['total_completion_tokens']:,}")
    print(f"   总 tokens：{stats['total_tokens']:,}\n")

    if stats["requests"]:
        print(f"📈 最近请求：")
        for req in stats["requests"][-5:][::-1]:
            print(f"   {req['timestamp'][:19]} | {req['model']:20s} | "
                  f"↓{req['prompt_tokens']:5d} ↑{req['completion_tokens']:5d} | "
                  f"total: {req['total_tokens']}")
    print()

    print(f"📁 日志文件：")
    print(f"   简要统计：{SUMMARY_FILE}")
    print(f"   详细记录：{DETAILED_FILE}")
    print(f"   请求日志：{REQUESTS_LOG}")
    print(f"\n🔧 使用方法：")
    print(f"   1. 启动代理：python3 {__file__}")
    print(f"   2. 修改 Ollama 端口为 8181（代理端口）")
    print(f"   3. 或直接使用 http://127.0.0.1:8181/api/chat")
    print(f"{'='*60}\n")


def main():
    """主函数"""
    global stats

    # 打印初始状态
    print_status()

    # 创建服务器
    server = HTTPServer((OLLAMA_HOST, PROXY_PORT), OllamaProxyHandler)
    print(f"🚀 代理服务器监听：http://{OLLAMA_HOST}:{PROXY_PORT}")
    print(f"📡 代理目标：http://{OLLAMA_HOST}:{OLLAMA_PORT}")
    print(f"💡 提示：将 Ollama 客户端指向 {PROXY_PORT} 端口\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n\n🛑 代理服务器已停止")
        print_status()
        server.shutdown()


if __name__ == "__main__":
    main()
