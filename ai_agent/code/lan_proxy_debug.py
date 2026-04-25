#!/usr/bin/env python3
"""
局域网代理 - 详细记录两边进出数据（urllib 版）
日志: /root/.openclaw/workspace/ai_agent/logs/lan_proxy_debug.log
"""

import http.server
import socketserver
import urllib.request
import urllib.error
import ssl
import json
import logging
import time
import os
from datetime import datetime

LOG_DIR = "/root/.openclaw/workspace/ai_agent/logs"
os.makedirs(LOG_DIR, exist_ok=True)

LOG_FILE = os.path.join(LOG_DIR, "lan_proxy_debug.log")

console_handler = logging.StreamHandler()
file_handler = logging.FileHandler(LOG_FILE, mode='a', encoding='utf-8')

logging.basicConfig(
    level=logging.DEBUG,
    format="%(message)s",
    handlers=[console_handler, file_handler]
)
logger = logging.getLogger("lan-proxy")

REMOTE_HOST = "58.23.129.98"
REMOTE_PORT = 8000
API_KEY = "sk-78sadn09bjawde123e"
LISTEN_HOST = "0.0.0.0"
LISTEN_PORT = 8765

def ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

def fix_response_body(body_bytes):
    """修复 content/reasoning 字段"""
    try:
        resp_json = json.loads(body_bytes)
        if "choices" in resp_json:
            for choice in resp_json["choices"]:
                msg = choice.get("message", {})
                if isinstance(msg, dict) and msg.get("content") is None and msg.get("reasoning"):
                    msg["content"] = msg["reasoning"]
        return json.dumps(resp_json, ensure_ascii=False).encode()
    except Exception:
        return body_bytes

def send_json_response(handler, status, data):
    """发送 JSON 响应"""
    body = json.dumps(data).encode()
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json")
    handler.send_header("Content-Length", str(len(body)))
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
    handler.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
    handler.end_headers()
    handler.wfile.write(body)

def proxy_and_handle(handler, method, body):
    """代理请求并记录详细日志"""
    path = handler.path
    client_ip = handler.client_address[0]
    
    request_start = ts()
    
    # ═══════════════════════════════════════════════════════
    #  ① 收到客户端请求
    # ═══════════════════════════════════════════════════════
    logger.info(f"{'='*70}")
    logger.info(f"📥 【INCOMING REQUEST】 {request_start}")
    logger.info(f"   来源: {client_ip}")
    logger.info(f"   请求: {method} {path}")
    logger.info(f"   头部: {dict(handler.headers)}")
    
    if body and len(body) > 0:
        try:
            body_str = body.decode('utf-8', errors='replace')
        except:
            body_str = f"[binary, {len(body)} bytes]"
        logger.info(f"   请求体 ({len(body)}B):")
        if len(body_str) > 2000:
            body_str = body_str[:2000] + f"\n... [truncated, total {len(body_str)} bytes]"
        try:
            json_obj = json.loads(body_str)
            pretty = json.dumps(json_obj, indent=2, ensure_ascii=False)
            for line in pretty.split('\n'):
                logger.info(f"     {line}")
        except:
            for line in body_str.split('\n'):
                logger.info(f"     {line}")
    else:
        logger.info(f"   请求体: (空)")
    
    # ═══════════════════════════════════════════════════════
    #  ② 发送请求到远程服务器
    # ═══════════════════════════════════════════════════════
    out_start = ts()
    logger.info(f"{'='*70}")
    logger.info(f"📤 【OUTGOING REQUEST】 {out_start}")
    logger.info(f"   目标: http://{REMOTE_HOST}:{REMOTE_PORT}{path}")
    
    remote_url = f"http://{REMOTE_HOST}:{REMOTE_PORT}{path}"
    
    headers = {
        "Authorization": f"Bearer {API_KEY}",
    }
    if method in ("POST", "PUT", "PATCH") and body:
        headers["Content-Type"] = "application/json"
    # 保留其他头
    skip_lower = {"connection", "content-length", "host", "transfer-encoding"}
    for k, v in handler.headers.items():
        if k.lower() not in skip_lower:
            headers[k] = v
    
    for k, v in headers.items():
        logger.info(f"   头: {k}: {v}")
    
    if body and len(body) > 0:
        logger.info(f"   请求体: {len(body)} bytes")
    
    # 创建 SSL 上下文（关闭验证，远程是 HTTP）
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    
    req = urllib.request.Request(remote_url, data=body, method=method)
    for k, v in headers.items():
        req.add_header(k, v)
    
    req_start = time.time()
    
    try:
        # ═══════════════════════════════════════════════════════
        #  ③ 收到远程响应
        # ═══════════════════════════════════════════════════════
        with urllib.request.urlopen(req, timeout=120, context=ctx) as resp:
            resp_body = resp.read()
            resp_elapsed = time.time() - req_start
            
            resp_end = ts()
            logger.info(f"{'='*70}")
            logger.info(f"📥 【REMOTE RESPONSE】 {resp_end}")
            logger.info(f"   状态: {resp.status} {resp.reason}")
            logger.info(f"   耗时: {resp_elapsed:.3f}s")
            logger.info(f"   大小: {len(resp_body)} bytes")
            logger.info(f"   远程头: {dict(resp.headers)}")
            logger.info(f"   响应体 ({len(resp_body)}B):")
            
            # 格式化输出
            try:
                resp_json = json.loads(resp_body)
                resp_body = fix_response_body(resp_body)
                pretty = json.dumps(json.loads(resp_body), indent=2, ensure_ascii=False)
                if len(pretty) > 5000:
                    pretty = pretty[:5000] + f"\n... [truncated, total {len(resp_body)} bytes]"
                for line in pretty.split('\n'):
                    logger.info(f"     {line}")
            except:
                for line in resp_body.decode('utf-8', errors='replace')[:2000].split('\n'):
                    logger.info(f"     {line}")
            
            # Token 用量
            try:
                resp_json = json.loads(resp_body)
                if "usage" in resp_json:
                    u = resp_json["usage"]
                    logger.info(f"   📊 Token: prompt={u.get('prompt_tokens','?')} → completion={u.get('completion_tokens','?')} → total={u.get('total_tokens','?')}")
            except:
                pass
            
            # ═══════════════════════════════════════════════════════
            #  ④ 发送响应给客户端
            # ═══════════════════════════════════════════════════════
            resp_end2 = ts()
            logger.info(f"{'='*70}")
            logger.info(f"📤 【CLIENT RESPONSE】 {resp_end2}")
            logger.info(f"   发送给: {client_ip}")
            logger.info(f"   状态: {resp.status}")
            logger.info(f"   大小: {len(resp_body)} bytes")
            logger.info(f"   总耗时: {time.time() - req_start:.3f}s")
            logger.info(f"{'='*70}")
            logger.info("")
            
            send_json_response(handler, resp.status, json.loads(resp_body))
    
    except urllib.error.HTTPError as e:
        err_end = ts()
        err_body = e.read()
        err_elapsed = time.time() - req_start
        logger.info(f"{'='*70}")
        logger.info(f"📥 【REMOTE ERROR】 {err_end}")
        logger.info(f"   状态: {e.code} {e.reason}")
        logger.info(f"   耗时: {err_elapsed:.3f}s")
        logger.info(f"   响应体: {err_body[:500]}")
        logger.info(f"{'='*70}")
        send_json_response(handler, e.code, json.loads(err_body))
    
    except Exception as e:
        err_end = ts()
        err_elapsed = time.time() - req_start
        logger.info(f"{'='*70}")
        logger.info(f"❌ 【ERROR】 {err_end}")
        logger.info(f"   {method} {path}")
        logger.info(f"   错误: {e}")
        logger.info(f"   耗时: {err_elapsed:.3f}s")
        logger.info(f"{'='*70}")
        send_json_response(handler, 502, {"error": f"Bad Gateway: {str(e)}"})

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
        pass  # 抑制默认日志

class ThreadedServer(socketserver.ThreadingMixIn, http.server.HTTPServer):
    allow_reuse_address = True
    daemon_threads = True

if __name__ == "__main__":
    print("=" * 60)
    print("🚀 局域网代理 (详细日志) 启动中...")
    print(f"📡 监听: {LISTEN_HOST}:{LISTEN_PORT}")
    print(f"📝 日志: {LOG_FILE}")
    print("=" * 60)
    
    with open(LOG_FILE, 'a') as f:
        f.write(f"\n{'='*60}\n代理重启: {ts()}\n{'='*60}\n")
    
    server = ThreadedServer((LISTEN_HOST, LISTEN_PORT), ProxyHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 代理已停止")
        server.shutdown()
