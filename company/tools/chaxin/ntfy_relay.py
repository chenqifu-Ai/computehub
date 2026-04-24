#!/usr/bin/env python3
"""
茶信中转 - 使用 ntfy.sh（免费，无需认证）
ntfy.sh 是免费的 pub/sub 服务，无需注册
"""

import json
import urllib.request
import urllib.parse
import time
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# ntfy.sh 配置
NTFY_TOPIC = "chaxin-chat"  # 消息主题
NTFY_SERVER = "https://ntfy.sh"

API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"

def ntfy_publish(topic, message):
    """发布消息到 ntfy.sh"""
    url = f"{NTFY_SERVER}/{topic}"
    headers = {
        "Content-Type": "application/json",
        "Title": "茶信消息",
        "Priority": "default"
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(message).encode(),
        headers=headers,
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": "ok"}
    except Exception as e:
        return {"error": str(e)}

def ntfy_subscribe(topic, since="10m"):
    """从 ntfy.sh 获取消息"""
    url = f"{NTFY_SERVER}/{topic}/json?since={since}"
    headers = {"Accept": "application/json"}
    req = urllib.request.Request(url, headers=headers)
    
    messages = []
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            for line in resp:
                if line:
                    try:
                        data = json.loads(line.decode())
                        if data.get("event") == "message":
                            messages.append(json.loads(data.get("message", "{}")))
                    except:
                        pass
    except Exception as e:
        return {"error": str(e), "messages": []}
    
    return {"status": "ok", "messages": messages}

class NtfyRelayHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")
    
    def check_auth(self):
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            return auth[7:] == API_KEY or auth[7:].startswith("node_")
        params = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
        return params.get('key', [''])[0] == API_KEY
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        if parsed.path == '/health':
            self._send_json({"status": "ok", "service": "ntfy-relay"})
            return
        
        if not self.check_auth():
            self._send_error(401, "Unauthorized")
            return
        
        if parsed.path == '/msg/recv':
            to = params.get('to', [''])[0]
            result = ntfy_subscribe(f"{NTFY_TOPIC}-{to}")
            self._send_json(result)
            return
        
        if parsed.path == '/node/list':
            result = ntfy_subscribe(f"{NTFY_TOPIC}-nodes")
            self._send_json(result)
            return
        
        self._send_error(404, "Not Found")
    
    def do_POST(self):
        if not self.check_auth():
            self._send_error(401, "Unauthorized")
            return
        
        parsed = urllib.parse.urlparse(self.path)
        content_length = int(self.headers.get('Content-Length', 0))
        
        try:
            data = json.loads(self.rfile.read(content_length).decode())
        except:
            self._send_error(400, "Invalid JSON")
            return
        
        if parsed.path == '/msg/send':
            msg = {
                "id": f"msg_{int(time.time()*1000)}_{data.get('from', 'unknown')}",
                "from": data.get('from', ''),
                "to": data.get('to', ''),
                "subject": data.get('subject', ''),
                "body": data.get('body', ''),
                "priority": data.get('priority', 'normal'),
                "timestamp": time.time()
            }
            result = ntfy_publish(f"{NTFY_TOPIC}-{data.get('to')}", msg)
            self._send_json({"status": "sent" if "ok" in result else "error", "msg_id": msg["id"]})
            return
        
        if parsed.path == '/node/register':
            result = ntfy_publish(f"{NTFY_TOPIC}-nodes", {
                "node_id": data.get('id'),
                "name": data.get('name', ''),
                "endpoint": data.get('endpoint', ''),
                "last_seen": time.time()
            })
            self._send_json(result)
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

def run_server(port=8083):
    print(f"[*] 茶信 ntfy.sh 中转服务启动")
    print(f"[*] 端口: {port}")
    print(f"[*] ntfy 主题: {NTFY_TOPIC}")
    print(f"[*] 无需认证，直接使用")
    server = HTTPServer(('0.0.0.0', port), NtfyRelayHandler)
    server.serve_forever()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8083
    run_server(port)