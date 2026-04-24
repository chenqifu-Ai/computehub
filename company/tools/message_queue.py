#!/usr/bin/env python3
"""
茶信 (ChaMsg) v2.0 - 智能体通信系统
运行在 Linux 主控服务器，支持智能体间异步通信

功能：
- 消息收发、广播
- 任务管理（创建、查询、完成）
- 心跳检测
- 智能体注册与状态
- 消息模板
- Webhook 通知
- 统计报表

启动: python3 message_queue.py
端口: 8080
认证: API Key
"""

import json
import sqlite3
import time
import os
import hashlib
import threading
from datetime import datetime, timedelta
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs
import logging

# ==================== 配置 ====================

CONFIG = {
    'port': 8080,
    'api_keys': {
        # 主 API Key
        '8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii': {
            'name': 'master',
            'role': 'admin',
            'permissions': ['all']
        }
    },
    'heartbeat_timeout': 120,  # 心跳超时（秒）
    'message_retention': 30,  # 消息保留天数
    'max_message_size': 65536,  # 最大消息大小
}

# 预注册智能体
REGISTERED_AGENTS = {
    '红茶': {'role': 'ceo', 'emoji': '🍵'},
    '老K': {'role': 'researcher', 'emoji': '📊'},
    '阿狸': {'role': 'executor', 'emoji': '⚙️'},
    '小信': {'role': 'monitor', 'emoji': '📡'},
    '老黑': {'role': 'engineer', 'emoji': '🔧'},
    '小智': {'role': 'remote_executor', 'emoji': '🤖'},
    '小龙虾': {'role': 'assistant', 'emoji': '🦞'},
}

# 数据库路径
DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')
DB_PATH = os.path.join(DATA_DIR, 'messages.db')

# 日志配置
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(DATA_DIR, 'chaxin.log')),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('chaxin')

# ==================== 数据库 ====================

def init_db():
    """初始化数据库表"""
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # 消息表
    c.execute('''CREATE TABLE IF NOT EXISTS messages
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sender TEXT NOT NULL,
                  recipient TEXT NOT NULL,
                  subject TEXT,
                  body TEXT,
                  priority TEXT DEFAULT 'normal',
                  category TEXT DEFAULT 'message',
                  read INTEGER DEFAULT 0,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # 任务表
    c.execute('''CREATE TABLE IF NOT EXISTS tasks
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  title TEXT NOT NULL,
                  description TEXT,
                  assignee TEXT NOT NULL,
                  assigner TEXT NOT NULL,
                  status TEXT DEFAULT 'pending',
                  priority TEXT DEFAULT 'normal',
                  due_date DATETIME,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                  completed_at DATETIME,
                  result TEXT)''')
    
    # 心跳表
    c.execute('''CREATE TABLE IF NOT EXISTS heartbeats
                 (agent TEXT PRIMARY KEY,
                  last_heartbeat DATETIME,
                  status TEXT DEFAULT 'online',
                  ip TEXT,
                  metadata TEXT)''')
    
    # 智能体状态表
    c.execute('''CREATE TABLE IF NOT EXISTS agents
                 (name TEXT PRIMARY KEY,
                  role TEXT,
                  status TEXT DEFAULT 'offline',
                  last_seen DATETIME,
                  registered_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # 消息模板表
    c.execute('''CREATE TABLE IF NOT EXISTS templates
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  name TEXT NOT NULL,
                  category TEXT,
                  subject TEXT,
                  body TEXT,
                  created_at DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    # 审计日志表
    c.execute('''CREATE TABLE IF NOT EXISTS audit_log
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                  action TEXT,
                  agent TEXT,
                  details TEXT)''')
    
    # 创建索引
    c.execute('CREATE INDEX IF NOT EXISTS idx_msg_recipient ON messages(recipient)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_msg_timestamp ON messages(timestamp)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_task_assignee ON tasks(assignee)')
    c.execute('CREATE INDEX IF NOT EXISTS idx_task_status ON tasks(status)')
    
    conn.commit()
    conn.close()
    logger.info(f"数据库初始化完成: {DB_PATH}")


# ==================== HTTP Handler ====================

class MessageHandler(BaseHTTPRequestHandler):
    """HTTP 请求处理器"""
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        logger.info(format % args)
    
    def check_auth(self):
        """检查 API Key 认证"""
        auth = self.headers.get('Authorization', '')
        if auth.startswith('Bearer '):
            token = auth[7:]
            if token in CONFIG['api_keys']:
                return CONFIG['api_keys'][token]
        # 也支持查询参数
        parsed = urlparse(self.path)
        params = parse_qs(parsed.query)
        token = params.get('key', [None])[0]
        if token and token in CONFIG['api_keys']:
            return CONFIG['api_keys'][token]
        return None
    
    def send_json(self, data, status=200):
        """发送 JSON 响应"""
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
    
    def send_error_json(self, code, message, status=400):
        """发送错误响应"""
        self.send_json({'code': code, 'error': message}, status)
    
    def read_body(self):
        """读取请求体"""
        content_length = int(self.headers.get('Content-Length', 0))
        if content_length > CONFIG['max_message_size']:
            return None
        if content_length == 0:
            return {}
        try:
            return json.loads(self.rfile.read(content_length).decode('utf-8'))
        except:
            return None
    
    def do_OPTIONS(self):
        """处理 CORS 预检请求"""
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, DELETE')
        self.send_header('Access-Control-Allow-Headers', 'Authorization, Content-Type')
        self.end_headers()
    
    def do_GET(self):
        """处理 GET 请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # 健康检查（无需认证）
        if path == '/health':
            self.send_json({'code': 200, 'status': 'ok', 'time': datetime.now().isoformat()})
            return
        
        if path == '/stats':
            self.handle_stats()
            return
        
        # 认证检查
        auth = self.check_auth()
        if not auth:
            self.send_error_json(401, 'Unauthorized')
            return
        
        # 路由
        if path.startswith('/msg/'):
            self.handle_msg_get(path[5:], parsed)
        elif path.startswith('/task/'):
            self.handle_task_get(path[6:], parsed)
        elif path.startswith('/agent/'):
            self.handle_agent_get(path[7:], parsed)
        elif path.startswith('/template/'):
            self.handle_template_get(path[10:], parsed)
        else:
            self.send_error_json(404, 'Not found')
    
    def do_POST(self):
        """处理 POST 请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # 认证检查
        auth = self.check_auth()
        if not auth:
            self.send_error_json(401, 'Unauthorized')
            return
        
        # 读取请求体
        data = self.read_body()
        if data is None:
            self.send_error_json(400, 'Invalid request body')
            return
        
        # 路由
        if path == '/msg/send':
            self.handle_msg_send(data)
        elif path == '/msg/broadcast':
            self.handle_msg_broadcast(data)
        elif path.startswith('/task/'):
            self.handle_task_post(path[6:], data)
        elif path.startswith('/agent/'):
            self.handle_agent_post(path[7:], data)
        elif path.startswith('/template/'):
            self.handle_template_post(path[10:], data)
        else:
            self.send_error_json(404, 'Not found')
    
    def do_DELETE(self):
        """处理 DELETE 请求"""
        parsed = urlparse(self.path)
        path = parsed.path
        
        # 认证检查
        auth = self.check_auth()
        if not auth:
            self.send_error_json(401, 'Unauthorized')
            return
        
        # 路由
        if path.startswith('/msg/'):
            self.handle_msg_delete(path[5:])
        elif path.startswith('/task/'):
            self.handle_task_delete(path[6:])
        else:
            self.send_error_json(404, 'Not found')
    
    # ==================== 消息接口 ====================
    
    def handle_msg_get(self, action, parsed):
        """处理消息 GET 请求"""
        params = parse_qs(parsed.query)
        
        if action == 'recv':
            self._msg_recv(params)
        elif action == 'list':
            self._msg_list(params)
        elif action == 'search':
            self._msg_search(params)
        elif action.startswith('id/'):
            self._msg_get(int(action.split('/')[1]))
        else:
            self.send_error_json(404, 'Unknown action')
    
    def _msg_recv(self, params):
        """接收未读消息"""
        recipient = params.get('to', [None])[0]
        limit = int(params.get('limit', [10])[0])
        mark_read = params.get('read', ['1'])[0] == '1'
        category = params.get('category', [None])[0]
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        sql = 'SELECT id, sender, recipient, subject, body, priority, category, read, timestamp FROM messages WHERE read=0'
        args = []
        
        if recipient:
            sql += ' AND recipient=?'
            args.append(recipient)
        if category:
            sql += ' AND category=?'
            args.append(category)
        
        sql += ' ORDER BY priority DESC, timestamp DESC LIMIT ?'
        args.append(limit)
        
        c.execute(sql, args)
        messages = []
        for row in c.fetchall():
            messages.append({
                'id': row[0],
                'from': row[1],
                'to': row[2],
                'subject': row[3],
                'body': row[4],
                'priority': row[5],
                'category': row[6],
                'read': row[7],
                'timestamp': row[8]
            })
            if mark_read:
                c.execute('UPDATE messages SET read=1 WHERE id=?', (row[0],))
        
        if mark_read:
            conn.commit()
        conn.close()
        
        self.send_json({'code': 200, 'count': len(messages), 'messages': messages})
    
    def _msg_list(self, params):
        """列出消息"""
        recipient = params.get('to', [None])[0]
        sender = params.get('from', [None])[0]
        category = params.get('category', [None])[0]
        limit = int(params.get('limit', [20])[0])
        offset = int(params.get('offset', [0])[0])
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        sql = 'SELECT id, sender, recipient, subject, body, priority, category, read, timestamp FROM messages WHERE 1=1'
        args = []
        
        if recipient:
            sql += ' AND recipient=?'
            args.append(recipient)
        if sender:
            sql += ' AND sender=?'
            args.append(sender)
        if category:
            sql += ' AND category=?'
            args.append(category)
        
        sql += ' ORDER BY timestamp DESC LIMIT ? OFFSET ?'
        args.extend([limit, offset])
        
        c.execute(sql, args)
        messages = [{
            'id': row[0],
            'from': row[1],
            'to': row[2],
            'subject': row[3],
            'body': row[4],
            'priority': row[5],
            'category': row[6],
            'read': row[7],
            'timestamp': row[8]
        } for row in c.fetchall()]
        conn.close()
        
        self.send_json({'code': 200, 'count': len(messages), 'messages': messages})
    
    def _msg_search(self, params):
        """搜索消息"""
        query = params.get('q', [''])[0]
        limit = int(params.get('limit', [20])[0])
        
        if not query:
            self.send_error_json(400, 'Missing search query')
            return
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        search_pattern = f'%{query}%'
        c.execute('''SELECT id, sender, recipient, subject, body, priority, category, read, timestamp 
                     FROM messages 
                     WHERE subject LIKE ? OR body LIKE ?
                     ORDER BY timestamp DESC LIMIT ?''',
                  (search_pattern, search_pattern, limit))
        
        messages = [{
            'id': row[0],
            'from': row[1],
            'to': row[2],
            'subject': row[3],
            'body': row[4],
            'priority': row[5],
            'category': row[6],
            'read': row[7],
            'timestamp': row[8]
        } for row in c.fetchall()]
        conn.close()
        
        self.send_json({'code': 200, 'query': query, 'count': len(messages), 'messages': messages})
    
    def _msg_get(self, msg_id):
        """获取单条消息"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, sender, recipient, subject, body, priority, category, read, timestamp FROM messages WHERE id=?', (msg_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            self.send_error_json(404, 'Message not found')
            return
        
        self.send_json({
            'code': 200,
            'message': {
                'id': row[0],
                'from': row[1],
                'to': row[2],
                'subject': row[3],
                'body': row[4],
                'priority': row[5],
                'category': row[6],
                'read': row[7],
                'timestamp': row[8]
            }
        })
    
    def handle_msg_send(self, data):
        """发送消息"""
        required = ['from', 'to']
        if not all(k in data for k in required):
            self.send_error_json(400, 'Missing required fields: from, to')
            return
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO messages (sender, recipient, subject, body, priority, category)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (data['from'], data['to'],
                   data.get('subject', ''),
                   data.get('body', ''),
                   data.get('priority', 'normal'),
                   data.get('category', 'message')))
        msg_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # 记录审计日志
        self._audit_log('msg_send', data['from'], {'to': data['to'], 'subject': data.get('subject', '')})
        
        self.send_json({
            'code': 200,
            'message': 'sent',
            'id': msg_id,
            'timestamp': datetime.now().isoformat()
        })
    
    def handle_msg_broadcast(self, data):
        """广播消息"""
        if 'from' not in data or 'body' not in data:
            self.send_error_json(400, 'Missing required fields: from, body')
            return
        
        # 获取所有注册的智能体
        recipients = [name for name in REGISTERED_AGENTS.keys() if name != data['from']]
        
        # 自定义接收者列表
        if 'to' in data:
            if isinstance(data['to'], list):
                recipients = data['to']
            else:
                recipients = [data['to']]
        
        conn = sqlite3.connect(DB_PATH)
        sent_ids = []
        for recipient in recipients:
            c = conn.cursor()
            c.execute('''INSERT INTO messages (sender, recipient, subject, body, priority, category)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (data['from'], recipient,
                       data.get('subject', '[广播]'),
                       data['body'],
                       data.get('priority', 'high'),
                       data.get('category', 'broadcast')))
            sent_ids.append(c.lastrowid)
        conn.commit()
        conn.close()
        
        self._audit_log('msg_broadcast', data['from'], {'recipients': recipients, 'subject': data.get('subject', '')})
        
        self.send_json({
            'code': 200,
            'message': 'broadcast sent',
            'recipients': recipients,
            'count': len(sent_ids),
            'ids': sent_ids
        })
    
    def handle_msg_delete(self, action):
        """删除消息"""
        if not action.startswith('id/'):
            self.send_error_json(400, 'Invalid action')
            return
        
        msg_id = int(action.split('/')[1])
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM messages WHERE id=?', (msg_id,))
        conn.commit()
        conn.close()
        
        self.send_json({'code': 200, 'message': 'deleted', 'id': msg_id})
    
    # ==================== 任务接口 ====================
    
    def handle_task_get(self, action, parsed):
        """处理任务 GET 请求"""
        params = parse_qs(parsed.query)
        
        if action == 'list':
            self._task_list(params)
        elif action == 'my':
            self._task_my(params)
        elif action.startswith('id/'):
            self._task_get(int(action.split('/')[1]))
        else:
            self.send_error_json(404, 'Unknown action')
    
    def _task_list(self, params):
        """列出所有任务"""
        status = params.get('status', [None])[0]
        assignee = params.get('assignee', [None])[0]
        limit = int(params.get('limit', [20])[0])
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        sql = 'SELECT id, title, description, assignee, assigner, status, priority, due_date, created_at, completed_at FROM tasks WHERE 1=1'
        args = []
        
        if status:
            sql += ' AND status=?'
            args.append(status)
        if assignee:
            sql += ' AND assignee=?'
            args.append(assignee)
        
        sql += ' ORDER BY priority DESC, created_at DESC LIMIT ?'
        args.append(limit)
        
        c.execute(sql, args)
        tasks = [{
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'assignee': row[3],
            'assigner': row[4],
            'status': row[5],
            'priority': row[6],
            'due_date': row[7],
            'created_at': row[8],
            'completed_at': row[9]
        } for row in c.fetchall()]
        conn.close()
        
        self.send_json({'code': 200, 'count': len(tasks), 'tasks': tasks})
    
    def _task_my(self, params):
        """获取我的任务"""
        assignee = params.get('assignee', [None])[0]
        if not assignee:
            self.send_error_json(400, 'Missing assignee')
            return
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''SELECT id, title, description, assignee, assigner, status, priority, due_date, created_at
                     FROM tasks WHERE assignee=? AND status IN ('pending', 'in_progress')
                     ORDER BY priority DESC, created_at DESC''', (assignee,))
        
        tasks = [{
            'id': row[0],
            'title': row[1],
            'description': row[2],
            'assignee': row[3],
            'assigner': row[4],
            'status': row[5],
            'priority': row[6],
            'due_date': row[7],
            'created_at': row[8]
        } for row in c.fetchall()]
        conn.close()
        
        self.send_json({'code': 200, 'count': len(tasks), 'tasks': tasks})
    
    def _task_get(self, task_id):
        """获取单个任务"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT id, title, description, assignee, assigner, status, priority, due_date, created_at, completed_at, result FROM tasks WHERE id=?', (task_id,))
        row = c.fetchone()
        conn.close()
        
        if not row:
            self.send_error_json(404, 'Task not found')
            return
        
        self.send_json({
            'code': 200,
            'task': {
                'id': row[0],
                'title': row[1],
                'description': row[2],
                'assignee': row[3],
                'assigner': row[4],
                'status': row[5],
                'priority': row[6],
                'due_date': row[7],
                'created_at': row[8],
                'completed_at': row[9],
                'result': row[10]
            }
        })
    
    def handle_task_post(self, action, data):
        """处理任务 POST 请求"""
        if action == 'create':
            self._task_create(data)
        elif action.startswith('status/'):
            self._task_update_status(int(action.split('/')[1]), data)
        elif action.startswith('complete/'):
            self._task_complete(int(action.split('/')[1]), data)
        else:
            self.send_error_json(404, 'Unknown action')
    
    def _task_create(self, data):
        """创建任务"""
        required = ['title', 'assignee', 'assigner']
        if not all(k in data for k in required):
            self.send_error_json(400, f'Missing required fields: {", ".join(required)}')
            return
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT INTO tasks (title, description, assignee, assigner, priority, due_date)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (data['title'], data.get('description', ''), data['assignee'], data['assigner'],
                   data.get('priority', 'normal'), data.get('due_date')))
        task_id = c.lastrowid
        conn.commit()
        conn.close()
        
        # 发送通知消息给被分配者
        c = sqlite3.connect(DB_PATH).cursor()
        c.execute('''INSERT INTO messages (sender, recipient, subject, body, priority, category)
                     VALUES (?, ?, ?, ?, ?, ?)''',
                  (data['assigner'], data['assignee'],
                   f'[任务] {data["title"]}',
                   f'您有新任务：{data["title"]}\n\n优先级: {data.get("priority", "normal")}\n截止: {data.get("due_date", "未设置")}',
                   data.get('priority', 'normal'),
                   'task'))
        conn.commit()
        conn.close()
        
        self._audit_log('task_create', data['assigner'], {'task_id': task_id, 'assignee': data['assignee']})
        
        self.send_json({'code': 200, 'message': 'task created', 'id': task_id})
    
    def _task_complete(self, task_id, data):
        """完成任务"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''UPDATE tasks SET status='completed', completed_at=?, result=? WHERE id=?''',
                  (datetime.now().isoformat(), data.get('result', ''), task_id))
        conn.commit()
        
        # 获取任务信息
        c.execute('SELECT assignee, assigner, title FROM tasks WHERE id=?', (task_id,))
        row = c.fetchone()
        conn.close()
        
        if row:
            # 通知任务分配者
            c = sqlite3.connect(DB_PATH).cursor()
            c.execute('''INSERT INTO messages (sender, recipient, subject, body, priority, category)
                         VALUES (?, ?, ?, ?, ?, ?)''',
                      (row[0], row[1],
                       f'[任务完成] {row[2]}',
                       f'任务已完成：{row[2]}\n\n结果: {data.get("result", "无")}',
                       'normal',
                       'task'))
            sqlite3.connect(DB_PATH).commit()
        
        self.send_json({'code': 200, 'message': 'task completed', 'id': task_id})
    
    def handle_task_delete(self, action):
        """删除任务"""
        if not action.startswith('id/'):
            self.send_error_json(400, 'Invalid action')
            return
        
        task_id = int(action.split('/')[1])
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('DELETE FROM tasks WHERE id=?', (task_id,))
        conn.commit()
        conn.close()
        
        self.send_json({'code': 200, 'message': 'task deleted', 'id': task_id})
    
    # ==================== 智能体接口 ====================
    
    def handle_agent_get(self, action, parsed):
        """处理智能体 GET 请求"""
        if action == 'list':
            self._agent_list()
        elif action == 'status':
            self._agent_status()
        elif action == 'heartbeat':
            self._agent_heartbeat_list()
        else:
            self.send_error_json(404, 'Unknown action')
    
    def _agent_list(self):
        """列出所有智能体"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT name, role, status, last_seen FROM agents')
        
        agents = {}
        # 从注册表获取
        for name, info in REGISTERED_AGENTS.items():
            agents[name] = {
                'role': info['role'],
                'emoji': info['emoji'],
                'status': 'offline',
                'last_seen': None
            }
        
        # 更新状态
        for row in c.fetchall():
            if row[0] in agents:
                agents[row[0]]['status'] = row[2]
                agents[row[0]]['last_seen'] = row[3]
        conn.close()
        
        self.send_json({'code': 200, 'count': len(agents), 'agents': agents})
    
    def _agent_status(self):
        """获取智能体在线状态摘要"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 统计在线/离线
        c.execute('SELECT COUNT(*) FROM agents WHERE status="online"')
        online = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM agents')
        total = c.fetchone()[0]
        
        # 最近心跳
        c.execute('SELECT agent, last_heartbeat FROM heartbeats ORDER BY last_heartbeat DESC LIMIT 10')
        recent = [{'agent': row[0], 'last_heartbeat': row[1]} for row in c.fetchall()]
        conn.close()
        
        self.send_json({
            'code': 200,
            'online': online,
            'offline': len(REGISTERED_AGENTS) - online,
            'total_registered': len(REGISTERED_AGENTS),
            'recent_heartbeats': recent
        })
    
    def _agent_heartbeat_list(self):
        """获取心跳列表"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('SELECT agent, last_heartbeat, status, ip FROM heartbeats ORDER BY last_heartbeat DESC')
        
        heartbeats = [{
            'agent': row[0],
            'last_heartbeat': row[1],
            'status': row[2],
            'ip': row[3]
        } for row in c.fetchall()]
        conn.close()
        
        self.send_json({'code': 200, 'count': len(heartbeats), 'heartbeats': heartbeats})
    
    def handle_agent_post(self, action, data):
        """处理智能体 POST 请求"""
        if action == 'heartbeat':
            self._agent_heartbeat(data)
        elif action == 'register':
            self._agent_register(data)
        else:
            self.send_error_json(404, 'Unknown action')
    
    def _agent_heartbeat(self, data):
        """记录心跳"""
        if 'agent' not in data:
            self.send_error_json(400, 'Missing agent')
            return
        
        agent = data['agent']
        ip = data.get('ip', self.client_address[0])
        metadata = json.dumps(data.get('metadata', {}))
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO heartbeats (agent, last_heartbeat, status, ip, metadata)
                     VALUES (?, ?, 'online', ?, ?)''',
                  (agent, datetime.now().isoformat(), ip, metadata))
        c.execute('''INSERT OR REPLACE INTO agents (name, role, status, last_seen)
                     VALUES (?, COALESCE((SELECT role FROM agents WHERE name=?), 
                             COALESCE((SELECT role FROM (SELECT ?) AS t WHERE ? IN (SELECT name FROM (SELECT json_each.value FROM json_each(?), (SELECT json_object()) AS registered_agents))))),
                             'online', ?)''',
                  (agent, agent, agent, agent, json.dumps(list(REGISTERED_AGENTS.keys())), datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        self.send_json({'code': 200, 'message': 'heartbeat recorded', 'agent': agent, 'time': datetime.now().isoformat()})
    
    def _agent_register(self, data):
        """注册智能体"""
        required = ['name', 'role']
        if not all(k in data for k in required):
            self.send_error_json(400, 'Missing required fields')
            return
        
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute('''INSERT OR REPLACE INTO agents (name, role, status, last_seen)
                     VALUES (?, ?, 'online', ?)''',
                  (data['name'], data['role'], datetime.now().isoformat()))
        conn.commit()
        conn.close()
        
        self.send_json({'code': 200, 'message': 'agent registered', 'name': data['name']})
    
    # ==================== 模板接口 ====================
    
    def handle_template_get(self, action, parsed):
        """处理模板 GET 请求"""
        params = parse_qs(parsed.query)
        
        if action == 'list':
            category = params.get('category', [None])[0]
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            if category:
                c.execute('SELECT id, name, category, subject FROM templates WHERE category=?', (category,))
            else:
                c.execute('SELECT id, name, category, subject FROM templates')
            
            templates = [{'id': row[0], 'name': row[1], 'category': row[2], 'subject': row[3]} for row in c.fetchall()]
            conn.close()
            self.send_json({'code': 200, 'count': len(templates), 'templates': templates})
        
        elif action.startswith('id/'):
            template_id = int(action.split('/')[1])
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('SELECT id, name, category, subject, body FROM templates WHERE id=?', (template_id,))
            row = c.fetchone()
            conn.close()
            
            if not row:
                self.send_error_json(404, 'Template not found')
                return
            
            self.send_json({'code': 200, 'template': {'id': row[0], 'name': row[1], 'category': row[2], 'subject': row[3], 'body': row[4]}})
        else:
            self.send_error_json(404, 'Unknown action')
    
    def handle_template_post(self, action, data):
        """处理模板 POST 请求"""
        if action == 'create':
            required = ['name', 'body']
            if not all(k in data for k in required):
                self.send_error_json(400, 'Missing required fields')
                return
            
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('INSERT INTO templates (name, category, subject, body) VALUES (?, ?, ?, ?)',
                      (data['name'], data.get('category', 'general'), data.get('subject', ''), data['body']))
            template_id = c.lastrowid
            conn.commit()
            conn.close()
            
            self.send_json({'code': 200, 'message': 'template created', 'id': template_id})
        else:
            self.send_error_json(404, 'Unknown action')
    
    # ==================== 统计接口 ====================
    
    def handle_stats(self):
        """获取系统统计"""
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        
        # 消息统计
        c.execute('SELECT COUNT(*) FROM messages')
        total_messages = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM messages WHERE read=0')
        unread_messages = c.fetchone()[0]
        
        # 今日消息
        today = datetime.now().strftime('%Y-%m-%d')
        c.execute('SELECT COUNT(*) FROM messages WHERE timestamp LIKE ?', (f'{today}%',))
        today_messages = c.fetchone()[0]
        
        # 任务统计
        c.execute('SELECT COUNT(*) FROM tasks')
        total_tasks = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM tasks WHERE status="pending"')
        pending_tasks = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM tasks WHERE status="in_progress"')
        active_tasks = c.fetchone()[0]
        c.execute('SELECT COUNT(*) FROM tasks WHERE status="completed"')
        completed_tasks = c.fetchone()[0]
        
        # 智能体状态
        c.execute('SELECT COUNT(*) FROM heartbeats WHERE datetime(last_heartbeat) > datetime(?)',
                  ((datetime.now() - timedelta(seconds=CONFIG['heartbeat_timeout'])).isoformat(),))
        online_agents = c.fetchone()[0]
        
        # 按发送者统计
        c.execute('SELECT sender, COUNT(*) as cnt FROM messages GROUP BY sender ORDER BY cnt DESC LIMIT 5')
        top_senders = [{'sender': row[0], 'count': row[1]} for row in c.fetchall()]
        
        # 按接收者统计
        c.execute('SELECT recipient, COUNT(*) as cnt FROM messages GROUP BY recipient ORDER BY cnt DESC LIMIT 5')
        top_recipients = [{'recipient': row[0], 'count': row[1]} for row in c.fetchall()]
        
        conn.close()
        
        self.send_json({
            'code': 200,
            'messages': {
                'total': total_messages,
                'unread': unread_messages,
                'today': today_messages
            },
            'tasks': {
                'total': total_tasks,
                'pending': pending_tasks,
                'active': active_tasks,
                'completed': completed_tasks
            },
            'agents': {
                'online': online_agents,
                'registered': len(REGISTERED_AGENTS)
            },
            'top_senders': top_senders,
            'top_recipients': top_recipients,
            'uptime': datetime.now().isoformat()
        })
    
    # ==================== 辅助方法 ====================
    
    def _audit_log(self, action, agent, details):
        """记录审计日志"""
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            c.execute('INSERT INTO audit_log (action, agent, details) VALUES (?, ?, ?)',
                      (action, agent, json.dumps(details, ensure_ascii=False)))
            conn.commit()
            conn.close()
        except:
            pass


# ==================== 心跳清理线程 ====================

def heartbeat_cleanup():
    """定期清理过期心跳"""
    while True:
        time.sleep(60)  # 每分钟检查一次
        try:
            conn = sqlite3.connect(DB_PATH)
            c = conn.cursor()
            timeout = (datetime.now() - timedelta(seconds=CONFIG['heartbeat_timeout'])).isoformat()
            c.execute('UPDATE agents SET status="offline" WHERE name IN (SELECT agent FROM heartbeats WHERE last_heartbeat < ?)',
                      (timeout,))
            conn.commit()
            conn.close()
        except:
            pass


# ==================== 主程序 ====================

def run_server(port=None):
    """启动服务器"""
    port = port or CONFIG['port']
    init_db()
    
    # 启动心跳清理线程
    cleanup_thread = threading.Thread(target=heartbeat_cleanup, daemon=True)
    cleanup_thread.start()
    
    server = HTTPServer(('0.0.0.0', port), MessageHandler)
    logger.info(f'茶信服务启动 v2.0')
    logger.info(f'端口: {port}')
    logger.info(f'数据库: {DB_PATH}')
    logger.info(f'智能体: {len(REGISTERED_AGENTS)} 个已注册')
    logger.info('按 Ctrl+C 停止')
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info('服务停止')


if __name__ == '__main__':
    import sys
    port = int(sys.argv[1]) if len(sys.argv) > 1 else CONFIG['port']
    run_server(port)