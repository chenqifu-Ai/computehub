#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
茶信本地中转 - 直接转发到红茶
跳过云端，局域网直连
"""

import json
import urllib.request
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

# 配置
LOCAL_PORT = 8080
HONGCHA_URL = "http://192.168.1.3:8080"
API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"

class LocalRelayHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{time.strftime('%H:%M:%S')}] {format % args}")
    
    def do_GET(self):
        if self.path == '/health':
            self._send_json({"status": "ok", "service": "local-relay"})
            return
        
        # 转发到红茶
        try:
            url = f"{HONGCHA_URL}{self.path}"
            req = urllib.request.Request(url)
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(data)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)
    
    def do_POST(self):
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            data = self.rfile.read(content_length)
            
            # 转发到红茶
            url = f"{HONGCHA_URL}{self.path}"
            req = urllib.request.Request(url, data=data, method='POST')
            req.add_header('Content-Type', 'application/json')
            
            with urllib.request.urlopen(req, timeout=5) as resp:
                resp_data = resp.read()
                self.send_response(200)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()
                self.wfile.write(resp_data)
        except Exception as e:
            self._send_json({"error": str(e)}, 500)
    
    def _send_json(self, data, status=200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode())

def run_server(port=8080):
    print(f"[*] 茶信本地中转启动")
    print(f"[*] 端口: {port}")
    print(f"[*] 转发到: {HONGCHA_URL}")
    
    server = HTTPServer(('0.0.0.0', port), LocalRelayHandler)
    server.serve_forever()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8080
    run_server(port)