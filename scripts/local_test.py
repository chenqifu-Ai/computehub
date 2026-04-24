#!/usr/bin/env python3
"""
本地测试服务器 - 使用127.0.0.1
"""

from http.server import HTTPServer, BaseHTTPRequestHandler

class LocalHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"Hello from local server!\n")

def run_server():
    server = HTTPServer(('127.0.0.1', 8081), LocalHandler)
    print("本地测试服务器启动在 http://127.0.0.1:8081")
    server.serve_forever()

if __name__ == "__main__":
    run_server()