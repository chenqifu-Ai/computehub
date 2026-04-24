#!/usr/bin/env python3
"""
茶信云存储 - 使用 GitHub Gist 作为免费消息存储
GitHub Gist 免费，可以存储文件

使用方法：
1. 创建一个 GitHub Token (https://github.com/settings/tokens)
2. 创建一个 Gist
3. 用这个脚本读写消息
"""

import json
import urllib.request
import urllib.parse
import time
import os

# GitHub Token（需要用户创建）
# 访问 https://github.com/settings/tokens/new
# 勾选 gist 权限
GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN", "")

# Gist ID（创建后获取）
GIST_ID = os.environ.get("GIST_ID", "")

API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"

def github_request(url, data=None, method='GET'):
    """发送GitHub API请求"""
    headers = {
        'Authorization': f'token {GITHUB_TOKEN}',
        'Accept': 'application/vnd.github.v3+json'
    }
    
    if data:
        data = json.dumps(data).encode()
        headers['Content-Type'] = 'application/json'
    
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except Exception as e:
        return {"error": str(e)}

def create_gist():
    """创建新的Gist"""
    url = "https://api.github.com/gists"
    data = {
        "description": "茶信消息存储",
        "public": False,
        "files": {
            "messages.json": {
                "content": json.dumps({"messages": {}, "nodes": {}}, ensure_ascii=False)
            }
        }
    }
    result = github_request(url, data, 'POST')
    return result.get('id')

def read_gist():
    """读取Gist内容"""
    if not GIST_ID:
        return {"error": "GIST_ID not set"}
    url = f"https://api.github.com/gists/{GIST_ID}"
    result = github_request(url)
    if 'files' in result:
        content = result['files'].get('messages.json', {}).get('content', '{}')
        return json.loads(content)
    return result

def update_gist(data):
    """更新Gist内容"""
    if not GIST_ID:
        return {"error": "GIST_ID not set"}
    url = f"https://api.github.com/gists/{GIST_ID}"
    update_data = {
        "files": {
            "messages.json": {
                "content": json.dumps(data, ensure_ascii=False, indent=2)
            }
        }
    }
    return github_request(url, update_data, 'PATCH')

def send_message(to, from_, subject, body, priority="normal"):
    """发送消息"""
    data = read_gist()
    if "error" in data:
        return data
    
    msg_id = f"msg_{int(time.time()*1000)}_{from_}"
    msg = {
        "id": msg_id,
        "from": from_,
        "to": to,
        "subject": subject,
        "body": body,
        "priority": priority,
        "timestamp": time.time()
    }
    
    if to not in data.get("messages", {}):
        data["messages"] = data.get("messages", {})
        data["messages"][to] = []
    
    data["messages"][to].append(msg)
    
    result = update_gist(data)
    return {"status": "sent", "msg_id": msg_id} if "error" not in result else result

def recv_message(to, limit=10):
    """接收消息"""
    data = read_gist()
    if "error" in data:
        return {"status": "error", "messages": [], "error": data["error"]}
    
    messages = data.get("messages", {}).get(to, [])[-limit:]
    
    # 取出后删除
    if to in data.get("messages", {}):
        data["messages"][to] = data["messages"][to][:-limit] if len(data["messages"][to]) > limit else []
        update_gist(data)
    
    return {"status": "ok", "messages": messages}

def register_node(node_id, name, endpoint):
    """注册节点"""
    data = read_gist()
    if "error" in data:
        return data
    
    data["nodes"] = data.get("nodes", {})
    data["nodes"][node_id] = {
        "name": name,
        "endpoint": endpoint,
        "last_seen": time.time()
    }
    
    result = update_gist(data)
    return {"status": "registered", "node_id": node_id} if "error" not in result else result

def list_nodes():
    """列出节点"""
    data = read_gist()
    if "error" in data:
        return data
    return {"status": "ok", "nodes": data.get("nodes", {})}

# 简单的HTTP服务
from http.server import HTTPServer, BaseHTTPRequestHandler

class GistRelayHandler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        print(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {format % args}")
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        params = urllib.parse.parse_qs(parsed.query)
        
        if parsed.path == '/health':
            self._send_json({"status": "ok", "service": "gist-relay"})
            return
        
        if parsed.path == '/msg/recv':
            to = params.get('to', [''])[0]
            limit = int(params.get('limit', [10])[0])
            result = recv_message(to, limit)
            self._send_json(result)
            return
        
        if parsed.path == '/node/list':
            result = list_nodes()
            self._send_json(result)
            return
        
        self._send_error(404, "Not Found")
    
    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == '/msg/send':
            content_length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(content_length).decode())
            result = send_message(
                data.get('to'),
                data.get('from'),
                data.get('subject', ''),
                data.get('body', ''),
                data.get('priority', 'normal')
            )
            self._send_json(result)
            return
        
        if parsed.path == '/node/register':
            content_length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(content_length).decode())
            result = register_node(
                data.get('id'),
                data.get('name'),
                data.get('endpoint', '')
            )
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

def run_server(port=8082):
    print(f"[*] 茶信Gist中转服务启动")
    print(f"[*] 端口: {port}")
    print(f"[*] 需要: GITHUB_TOKEN 和 GIST_ID")
    
    if not GITHUB_TOKEN:
        print("[!] 警告: GITHUB_TOKEN 未设置")
        print("[!] 请设置: export GITHUB_TOKEN=你的GitHub令牌")
    
    if not GIST_ID:
        print("[!] GIST_ID 未设置，正在创建新的Gist...")
        gid = create_gist()
        if gid:
            print(f"[!] 新Gist已创建: {gid}")
            print(f"[!] 请设置: export GIST_ID={gid}")
    
    server = HTTPServer(('0.0.0.0', port), GistRelayHandler)
    server.serve_forever()

if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8082
    run_server(port)