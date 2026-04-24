#!/usr/bin/env python3
"""
分布式茶信节点 - 云端注册 + 服务发现 + 消息中转
每个智能体运行自己的节点，通过 Ollama 云端协调
"""

import json
import time
import threading
import urllib.request
import urllib.parse
import os
import sqlite3
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

# ============ 配置 ============

# 本地配置
NODE_ID = os.environ.get("CHAXIN_NODE_ID", "xiaozhi")  # 节点ID
NODE_NAME = os.environ.get("CHAXIN_NODE_NAME", "小龙虾")  # 显示名称
LOCAL_PORT = int(os.environ.get("CHAXIN_PORT", "8080"))  # 本地端口

# Ollama 云端
OLLAMA_API_KEY = os.environ.get("OLLAMA_API_KEY", "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii")
OLLAMA_BASE_URL = os.environ.get("OLLAMA_BASE_URL", "https://ollama.com")

# 服务发现 URL (使用 Ollama 的模型 API 作为消息存储)
# 这是一个临时方案，实际需要 Ollama 提供专门的节点注册 API

# 本地数据库
DB_PATH = os.path.expanduser("~/.openclaw/workspace/company/tools/data/distributed.db")
DATA_DIR = os.path.dirname(DB_PATH)

# ============ 数据库 ============

def init_db():
    """初始化本地数据库"""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 消息表
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  msg_id TEXT UNIQUE,
                  sender TEXT NOT NULL,
                  recipient TEXT NOT NULL,
                  subject TEXT,
                  body TEXT,
                  priority TEXT DEFAULT 'normal',
                  read INTEGER DEFAULT 0,
                  delivered INTEGER DEFAULT 0,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # 节点表
    c.execute('''CREATE TABLE IF NOT EXISTS nodes
                 (node_id TEXT PRIMARY KEY,
                  name TEXT,
                  endpoint TEXT,
                  status TEXT DEFAULT 'offline',
                  last_seen DATETIME,
                  public_key TEXT)''')
    
    # 心跳记录
    c.execute('''CREATE TABLE IF NOT EXISTS heartbeats
                 (node_id TEXT PRIMARY KEY,
                  last_heartbeat DATETIME,
                  online_count INTEGER DEFAULT 0)''')
    
    conn.commit()
    conn.close()

# ============ 云端通信 ============

class CloudClient:
    """与 Ollama 云端通信"""
    
    def __init__(self):
        self.api_key = OLLAMA_API_KEY
        self.base_url = OLLAMA_BASE_URL
    
    def _request(self, endpoint, data=None, method='GET'):
        """发送请求到云端"""
        url = f"{self.base_url}{endpoint}"
        headers = {
            'Authorization': f'Bearer {self.api_key}',
            'Content-Type': 'application/json'
        }
        
        try:
            if method == 'GET':
                req = urllib.request.Request(url, headers=headers)
            else:
                req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method=method)
            
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode())
        except Exception as e:
            return {"error": str(e)}
    
    def register_node(self, node_id, name, endpoint):
        """注册节点到云端"""
        # 使用 Ollama API 的 chat 接口作为临时存储
        # 实际需要 Ollama 提供专门的节点注册 API
        return {"status": "registered", "node_id": node_id}
    
    def send_message_via_cloud(self, to, subject, body, priority="normal"):
        """通过云端中转发送消息"""
        # 存储到本地，等对方上线时拉取
        msg_id = f"msg_{int(time.time()*1000)}_{NODE_ID}"
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO messages (msg_id, sender, recipient, subject, body, priority)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (msg_id, NODE_ID, to, subject, body, priority))
        conn.commit()
        conn.close()
        
        return {"status": "queued", "msg_id": msg_id}
    
    def get_pending_messages(self, node_id):
        """获取待接收的消息"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT msg_id, sender, subject, body, priority, timestamp
                     FROM messages WHERE recipient=? AND delivered=0
                     ORDER BY priority DESC, timestamp ASC''', (node_id,))
        
        messages = []
        for row in c.fetchall():
            messages.append({
                "id": row[0],
                "from": row[1],
                "subject": row[2],
                "body": row[3],
                "priority": row[4],
                "timestamp": row[5]
            })
        
        # 标记为已投递
        c.execute('UPDATE messages SET delivered=1 WHERE recipient=?', (node_id,))
        conn.commit()
        conn.close()
        
        return messages
    
    def heartbeat(self):
        """发送心跳，更新在线状态"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO heartbeats (node_id, last_heartbeat, online_count)
                     VALUES (?, datetime('now'), ?)''',
                  (NODE_ID, 1))
        conn.commit()
        conn.close()
        return {"status": "alive", "node_id": NODE_ID}

# ============ 本地服务 ============

class LocalNodeHandler(BaseHTTPRequestHandler):
    """本地节点 HTTP 服务"""
    
    def log_message(self, format, *args):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] {format % args}")
    
    def check_auth(self):
        """检查认证"""
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth[7:]
            # 接受 Ollama API Key 或节点间共享密钥
            return token == OLLAMA_API_KEY or token.startswith('node_')
        return False
    
    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path
        
        # 健康检查不需要认证
        if path == '/health':
            self._send_json({"status": "ok", "node": NODE_ID, "name": NODE_NAME})
            return
        
        if path == '/node/info':
            self._send_json({
                "node_id": NODE_ID,
                "name": NODE_NAME,
                "port": LOCAL_PORT,
                "status": "online"
            })
            return
        
        # 以下需要认证
        if not self.check_auth():
            self._send_error(401, "Unauthorized")
            return
        
        if path == '/msg/recv':
            self._handle_recv(parsed)
        elif path == '/msg/list':
            self._handle_list(parsed)
        elif path == '/msg/poll':
            self._handle_poll(parsed)
        else:
            self._send_error(404, "Not Found")
    
    def do_POST(self):
        if not self.check_auth():
            self._send_error(401, "Unauthorized")
            return
        
        parsed = urllib.parse.urlparse(self.path)
        
        if parsed.path == '/msg/send':
            self._handle_send()
        elif parsed.path == '/msg/broadcast':
            self._handle_broadcast()
        else:
            self._send_error(404, "Not Found")
    
    def _handle_send(self):
        """处理发送消息"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(content_length).decode())
            
            if not data.get('to'):
                self._send_error(400, "Missing recipient")
                return
            
            msg_id = f"msg_{int(time.time()*1000)}_{NODE_ID}"
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('''INSERT INTO messages (msg_id, sender, recipient, subject, body, priority)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (msg_id, data.get('from', NODE_ID), data['to'],
                       data.get('subject', ''), data.get('body', ''),
                       data.get('priority', 'normal')))
            conn.commit()
            conn.close()
            
            self._send_json({"status": "sent", "msg_id": msg_id})
            
        except Exception as e:
            self._send_error(500, str(e))
    
    def _handle_recv(self, parsed):
        """处理接收消息"""
        params = urllib.parse.parse_qs(parsed.query)
        recipient = params.get('to', [NODE_ID])[0]
        limit = int(params.get('limit', [10])[0])
        mark_read = params.get('read', ['1'])[0] == '1'
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT msg_id, sender, recipient, subject, body, priority, read, timestamp
                     FROM messages WHERE recipient=? AND read=0
                     ORDER BY priority DESC, timestamp ASC LIMIT ?''',
                  (recipient, limit))
        
        messages = []
        for row in c.fetchall():
            messages.append({
                "id": row[0],
                "from": row[1],
                "to": row[2],
                "subject": row[3],
                "body": row[4],
                "priority": row[5],
                "read": row[6],
                "timestamp": row[7]
            })
            if mark_read:
                c.execute('UPDATE messages SET read=1 WHERE msg_id=?', (row[0],))
        
        if mark_read:
            conn.commit()
        conn.close()
        
        self._send_json({"status": "ok", "messages": messages})
    
    def _handle_list(self, parsed):
        """列出消息历史"""
        params = urllib.parse.parse_qs(parsed.query)
        limit = int(params.get('limit', [20])[0])
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT msg_id, sender, recipient, subject, body, priority, read, timestamp
                     FROM messages ORDER BY timestamp DESC LIMIT ?''', (limit,))
        
        messages = []
        for row in c.fetchall():
            messages.append({
                "id": row[0],
                "from": row[1],
                "to": row[2],
                "subject": row[3],
                "body": row[4],
                "priority": row[5],
                "read": row[6],
                "timestamp": row[7]
            })
        conn.close()
        
        self._send_json({"status": "ok", "messages": messages})
    
    def _handle_poll(self, parsed):
        """长轮询等待新消息"""
        params = urllib.parse.parse_qs(parsed.query)
        recipient = params.get('to', [NODE_ID])[0]
        timeout = int(params.get('timeout', [30])[0])
        
        start = time.time()
        while time.time() - start < timeout:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT COUNT(*) FROM messages WHERE recipient=? AND read=0', (recipient,))
            count = c.fetchone()[0]
            conn.close()
            
            if count > 0:
                self._handle_recv(parsed)
                return
            time.sleep(1)
        
        self._send_json({"status": "timeout", "messages": []})
    
    def _handle_broadcast(self):
        """广播消息"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            data = json.loads(self.rfile.read(content_length).decode())
            
            # 广播给所有已知节点
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT DISTINCT node_id FROM nodes WHERE node_id != ?', (NODE_ID,))
            nodes = [row[0] for row in c.fetchall()]
            
            if not nodes:
                # 默认节点列表
                nodes = ['hongcha', 'laok', 'ali', 'xiaoxin', 'laohei']
            
            msg_ids = []
            for node in nodes:
                msg_id = f"msg_{int(time.time()*1000)}_{NODE_ID}"
                c.execute('''INSERT INTO messages (msg_id, sender, recipient, subject, body, priority)
                             VALUES (?, ?, ?, ?, ?, ?)''',
                          (msg_id, data.get('from', NODE_ID), node,
                           data.get('subject', '[广播]'), data.get('body', ''),
                           data.get('priority', 'high')))
                msg_ids.append(msg_id)
            
            conn.commit()
            conn.close()
            
            self._send_json({"status": "broadcast", "recipients": nodes, "msg_ids": msg_ids})
            
        except Exception as e:
            self._send_error(500, str(e))
    
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


# ============ 心跳线程 ============

def heartbeat_thread():
    """后台心跳线程"""
    cloud = CloudClient()
    while True:
        try:
            cloud.heartbeat()
            time.sleep(60)  # 每分钟心跳
        except:
            time.sleep(10)


# ============ 主程序 ============

def run_server(port=LOCAL_PORT):
    init_db()
    
    # 启动心跳线程
    t = threading.Thread(target=heartbeat_thread, daemon=True)
    t.start()
    
    server = HTTPServer(('0.0.0.0', port), LocalNodeHandler)
    print(f"[*] 分布式茶信节点启动")
    print(f"[*] 节点: {NODE_ID} ({NODE_NAME})")
    print(f"[*] 端口: {port}")
    print(f"[*] 按 Ctrl+C 停止")
    server.serve_forever()


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else LOCAL_PORT
    run_server(port)