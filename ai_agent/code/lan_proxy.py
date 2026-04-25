#!/usr/bin/env python3
"""
局域网代理 - 将远程 Qwen 3.6 35B API 代理到局域网
监听 0.0.0.0:8765, 转发到 58.23.129.98:8000
其他局域网设备可访问: http://192.168.1.17:8765/v1/...
纯标准库，无需额外依赖
"""

import http.server
import socketserver
import http.client
import json
import logging
import time
import io

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)
logger = logging.getLogger("lan-proxy")

REMOTE_HOST = "58.23.129.98"
REMOTE_PORT = 8000
API_KEY = "sk-78sadn09bjawde123e"
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8765

def build_proxy_headers(headers_dict):
    """构建代理请求头，去掉连接相关头"""
    skip = {"connection", "content-length", "host", "transfer-encoding"}
    return {k: v for k, v in headers_dict.items() if k.lower() not in skip}

def fix_response_body(body_bytes):
    """修复 content/reasoning 字段问题"""
    try:
        resp_json = json.loads(body_bytes)
        if "choices" in resp_json:
            for choice in resp_json["choices"]:
                msg = choice.get("message", {})
                if isinstance(msg, dict):
                    if msg.get("content") is None and msg.get("reasoning"):
                        msg["content"] = msg["reasoning"]
                        if "x_reasoning" not in msg:
                            msg["x_reasoning"] = msg["reasoning"]
        return json.dumps(resp_json, ensure_ascii=False).encode()
    except Exception:
        return body_bytes

def send_response_to_client(handler, status, body_bytes):
    """将响应发送回客户端"""
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body_bytes)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.end_headers()
    handler.wfile.write(body_bytes)

def proxy_and_handle(handler, method, body):
    """完整的代理流程"""
    path = handler.path
    remote_url = path  # e.g. /v1/models
    
    # 连接到远程服务器
    conn = http.client.HTTPConnection(REMOTE_HOST, REMOTE_PORT, timeout=120)
    
    try:
        # 构建请求头
        proxy_headers = {
            "Authorization": f"Bearer {API_KEY}",
        }
        # 添加 Content-Type（有 body 时）
        if body is not None and len(body) > 0:
            proxy_headers["Content-Type"] = "application/json"
        # 保留其他头
        orig_headers = build_proxy_headers(dict(handler.headers))
        proxy_headers.update(orig_headers)
        
        # GET/DELETE 不传 body
        send_body = body if method in ("POST", "PUT", "PATCH") else None
        
        start = time.time()
        conn.request(method, remote_url, body=send_body, headers=proxy_headers)
        resp = conn.getresponse()
        elapsed = time.time() - start
        
        resp_body = resp.read()
        
        # 修复 AI 响应格式
        resp_body = fix_response_body(resp_body)
        
        logger.info(f"{method} {path} -> {resp.status} ({elapsed:.2f}s)")
        send_response_to_client(handler, resp.status, resp_body)
    
    except Exception as e:
        logger.error(f"{method} {path} 错误: {e}")
        err_body = json.dumps({"error": f"Bad Gateway: {str(e)}"}).encode()
        send_response_to_client(handler, 502, err_body)
    
    finally:
        conn.close()

class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        proxy_and_handle(self, "GET", None)
    
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None
        proxy_and_handle(self, "POST", body)
    
    def do_OPTIONS(self):
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()
    
    def do_PUT(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else None
        proxy_and_handle(self, "PUT", body)
    
    def do_DELETE(self):
        proxy_and_handle(self, "DELETE", None)
    
    def log_message(self, format, *args):
        logger.info(f"{self.client_address[0]} - {format % args}")

class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 局域网代理启动中...")
    print(f"📡 监听: {LISTEN_HOST}:{LISTEN_PORT}")
    print(f"🎯 转发: {REMOTE_HOST}:{REMOTE_PORT}/v1")
    print(f"📱 局域网访问: http://192.168.1.17:{LISTEN_PORT}/v1/...")
    print("=" * 60)
    
    server = ThreadedServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 代理已停止")
        server.shutdown()
