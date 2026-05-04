#!/usr/bin/env python3
"""
测试HTTP服务器
"""

from http.server import HTTPServer, BaseHTTPRequestHandler

class TestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(b"
        <!DOCTYPE html>
        <html>
        <head>
            <title>测试页面</title>
            <style>
                body { background: #667eea; color: white; font-family: Arial; text-align: center; padding: 50px; }
            </style>
        </head>
        <body>
            <h1>✅ 服务器正常运行</h1>
            <p>端口8081服务正常</p>
        </body>
        </html>
        ")

def run_server():
    server = HTTPServer(('0.0.0.0', 8081), TestHandler)
    print("测试服务器启动在 http://localhost:8081")
    server.serve_forever()

if __name__ == "__main__":
    run_server()