#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
充电云 - 本地开发服务器
启动方式: python3 server.py
访问地址: http://localhost:8080
"""

import http.server
import socketserver
import os
import webbrowser
from functools import partial

PORT = 8080
DIRECTORY = os.path.dirname(os.path.abspath(__file__))

class Handler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=DIRECTORY, **kwargs)
    
    def do_GET(self):
        # 默认页面跳转到登录页
        if self.path == '/' or self.path == '':
            self.path = '/login.html'
        return super().do_GET()
    
    def end_headers(self):
        # 添加CORS头
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        super().end_headers()

if __name__ == '__main__':
    os.chdir(DIRECTORY)
    
    print("=" * 50)
    print("⚡ 充电云 - 本地开发服务器")
    print("=" * 50)
    print(f"📁 服务目录: {DIRECTORY}")
    print(f"🌐 访问地址: http://localhost:{PORT}")
    print("")
    print("📋 页面导航:")
    print(f"   - 登录页: http://localhost:{PORT}/login.html")
    print(f"   - 管理后台: http://localhost:{PORT}/index.html")
    print(f"   - 官网首页: http://localhost:{PORT}/home.html")
    print("")
    print("🛑 按 Ctrl+C 停止服务器")
    print("=" * 50)
    
    try:
        with socketserver.TCPServer(("", PORT), Handler) as httpd:
            # 尝试打开浏览器
            # webbrowser.open(f'http://localhost:{PORT}')
            httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n✅ 服务器已停止")
    except OSError as e:
        if 'Address already in use' in str(e):
            print(f"❌ 端口 {PORT} 已被占用，请更换端口")
        else:
            print(f"❌ 启动失败: {e}")