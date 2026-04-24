#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
茶信客户端 - 使用 ntfy.sh 作为云端中转
免费，无需注册
"""

import json
import urllib.request
import urllib.parse
import time
import os

# 配置
NTFY_SERVER = os.environ.get("NTFY_SERVER", "https://ntfy.sh")
NTFY_TOPIC = os.environ.get("NTFY_TOPIC", "chaxin-chat")
API_KEY = os.environ.get("CHAXIN_API_KEY", "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii")

def send_message(to, subject="", body="", priority="normal", from_="xiaozhi"):
    """发送消息"""
    msg = {
        "id": f"msg_{int(time.time()*1000)}_{from_}",
        "from": from_,
        "to": to,
        "subject": subject,
        "body": body,
        "priority": priority,
        "timestamp": time.time()
    }
    
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}-{to}"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Title": (subject or "茶信消息").encode('utf-8').decode('latin-1'),
        "Priority": "high" if priority == "urgent" else "default"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(msg, ensure_ascii=False).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": "sent", "msg_id": msg["id"]}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def recv_messages(to, since="10m"):
    """接收消息"""
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}-{to}/json?since={since}"
    headers = {"Accept": "application/json"}
    req = urllib.request.Request(url, headers=headers)
    
    messages = []
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            for line in resp:
                if line:
                    try:
                        data = json.loads(line.decode('utf-8'))
                        if data.get("event") == "message":
                            # ntfy.sh 的消息在 message 字段
                            msg_str = data.get("message", "{}")
                            try:
                                msg = json.loads(msg_str)
                            except:
                                # 如果不是JSON，当作纯文本
                                msg = {"body": msg_str}
                            if msg.get("to") == to or msg.get("to") == "*" or not msg.get("to"):
                                messages.append(msg)
                    except:
                        pass
    except Exception as e:
        return {"status": "error", "error": str(e), "messages": []}
    
    return {"status": "ok", "messages": messages}

def register_node(node_id, name, endpoint):
    """注册节点"""
    msg = {
        "event": "register",
        "node_id": node_id,
        "name": name,
        "endpoint": endpoint,
        "last_seen": time.time()
    }
    
    url = f"{NTFY_SERVER}/{NTFY_TOPIC}-nodes"
    headers = {
        "Content-Type": "application/json; charset=utf-8",
        "Title": f"Node: {node_id}"
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(msg, ensure_ascii=False).encode('utf-8'),
        headers=headers,
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return {"status": "registered", "node_id": node_id}
    except Exception as e:
        return {"status": "error", "error": str(e)}

def check_connection():
    """检查连接"""
    try:
        url = f"{NTFY_SERVER}/{NTFY_TOPIC}-test/json?since=1s"
        with urllib.request.urlopen(url, timeout=5) as resp:
            return {"status": "ok", "server": NTFY_SERVER}
    except Exception as e:
        return {"status": "error", "server": NTFY_SERVER, "error": str(e)}

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python ntfy_client.py send <to> <subject> <body>")
        print("  python ntfy_client.py recv <to>")
        print("  python ntfy_client.py register <node_id> <name> <endpoint>")
        print("  python ntfy_client.py check")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "check":
        result = check_connection()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif cmd == "send":
        if len(sys.argv) < 5:
            print("用法: python ntfy_client.py send <to> <subject> <body>")
            sys.exit(1)
        result = send_message(sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif cmd == "recv":
        to = sys.argv[2] if len(sys.argv) > 2 else "xiaozhi"
        result = recv_messages(to)
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif cmd == "register":
        if len(sys.argv) < 5:
            print("用法: python ntfy_client.py register <node_id> <name> <endpoint>")
            sys.exit(1)
        result = register_node(sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps(result, indent=2, ensure_ascii=False))