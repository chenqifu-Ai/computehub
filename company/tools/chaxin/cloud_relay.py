#!/usr/bin/env python3
"""
消息中转服务 - 云函数版本
部署到阿里云FC/腾讯云SCF/Vercel

免费额度足够个人使用
"""

import json
import time
import hashlib
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

# ============ 配置 ============

# 消息存储（内存 + 持久化到文件）
MESSAGES = {}  # {recipient: [messages]}
NODES = {}      # {node_id: {endpoint, last_seen}}

# API Key
API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"

# 持久化文件
DATA_FILE = "/tmp/chaxin_relay.json"

def save_data():
    """持久化到文件"""
    try:
        with open(DATA_FILE, 'w') as f:
            json.dump({"messages": MESSAGES, "nodes": NODES}, f)
    except:
        pass

def load_data():
    """从文件加载"""
    try:
        with open(DATA_FILE, 'r') as f:
            data = json.load(f)
            MESSAGES.update(data.get("messages", {}))
            NODES.update(data.get("nodes", {}))
    except:
        pass

def verify_auth(auth_header):
    """验证认证"""
    if not auth_header:
        return False
    if auth_header.startswith("Bearer "):
        token = auth_header[7:]
        # 支持API Key或节点密钥
        return token == API_KEY or token.startswith("node_")
    return False

class RelayHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")

    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path
        params = parse_qs(parsed.query)

        # 健康检查
        if path == "/health":
            self._send_json({"status": "ok", "service": "chaxin-relay"})
            return

        # 认证检查
        if not verify_auth(self.headers.get('Authorization', '')):
            if params.get('key', [''])[0] != API_KEY:
                self._send_error(401, "Unauthorized")
                return

        # 节点注册
        if path == "/node/register":
            node_id = params.get('id', [''])[0]
            endpoint = params.get('endpoint', [''])[0]
            name = params.get('name', [node_id])[0]

            NODES[node_id] = {
                "name": name,
                "endpoint": endpoint,
                "last_seen": time.time()
            }
            save_data()
            self._send_json({"status": "registered", "node_id": node_id})
            return

        # 服务发现
        if path == "/node/list":
            self._send_json({"status": "ok", "nodes": NODES})
            return

        # 接收消息
        if path == "/msg/recv":
            recipient = params.get('to', [''])[0]
            limit = int(params.get('limit', [10])[0])

            if recipient not in MESSAGES:
                self._send_json({"status": "ok", "messages": []})
                return

            messages = MESSAGES[recipient][-limit:]
            # 取出后删除
            MESSAGES[recipient] = MESSAGES[recipient][:-limit] if len(MESSAGES[recipient]) > limit else []
            save_data()

            self._send_json({"status": "ok", "messages": messages})
            return

        self._send_error(404, "Not Found")

    def do_POST(self):
        parsed = urlparse(self.path)
        path = parsed.path

        # 认证检查
        if not verify_auth(self.headers.get('Authorization', '')):
            self._send_error(401, "Unauthorized")
            return

        # 读取请求体
        content_length = int(self.headers.get('Content-Length', 0))
        try:
            data = json.loads(self.rfile.read(content_length).decode())
        except:
            self._send_error(400, "Invalid JSON")
            return

        # 发送消息
        if path == "/msg/send":
            recipient = data.get('to', '')
            if not recipient:
                self._send_error(400, "Missing recipient")
                return

            msg = {
                "id": f"msg_{int(time.time()*1000)}_{data.get('from', 'unknown')}",
                "from": data.get('from', ''),
                "to": recipient,
                "subject": data.get('subject', ''),
                "body": data.get('body', ''),
                "priority": data.get('priority', 'normal'),
                "timestamp": time.time()
            }

            if recipient not in MESSAGES:
                MESSAGES[recipient] = []
            MESSAGES[recipient].append(msg)
            save_data()

            self._send_json({"status": "sent", "msg_id": msg["id"]})
            return

        self._send_error(404, "Not Found")

    def _send_json(self, data):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

    def _send_error(self, code, message):
        self.send_response(code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        self.wfile.write(json.dumps({"error": message}).encode())

def run_server(port=8081):
    load_data()
    server = HTTPServer(('0.0.0.0', port), RelayHandler)
    print(f"[*] 消息中转服务启动")
    print(f"[*] 端口: {port}")
    print(f"[*] 认证: API Key")
    print(f"[*] 按 Ctrl+C 停止")
    server.serve_forever()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8081
    run_server(port)