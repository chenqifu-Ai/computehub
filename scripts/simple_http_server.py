#!/usr/bin/env python3
"""
简单HTTP服务器 - 显示进程列表
"""

import subprocess
from http.server import HTTPServer, BaseHTTPRequestHandler

class ProcessHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            # 获取进程列表
            try:
                result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
                processes = result.stdout
                
                self.send_response(200)
                self.send_header('Content-type', 'text/plain; charset=utf-8')
                self.end_headers()
                self.wfile.write(f"📊 当前进程列表:\n\n{processes}".encode('utf-8'))
            except Exception as e:
                self.send_response(500)
                self.end_headers()
                self.wfile.write(f"错误: {str(e)}".encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server = HTTPServer(('0.0.0.0', 8081), ProcessHandler)
    print("🚀 简单进程监控启动在 http://localhost:8081")
    server.serve_forever()

if __name__ == "__main__":
    run_server()