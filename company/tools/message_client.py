#!/usr/bin/env python3
"""
消息客户端 - 小龙虾版
用于和红茶通信
"""

import urllib.request
import urllib.parse
import json
import os

# 茶信服务器地址
MSG_SERVER = os.environ.get("MSG_SERVER", "http://192.168.1.3:8080")

# Ollama API Key 认证
OLLAMA_API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"

def send_message(to, subject="", body="", priority="normal", from_="xiaozhi"):
    """发送消息"""
    data = {
        "from": from_,
        "to": to,
        "subject": subject,
        "body": body,
        "priority": priority
    }
    
    req = urllib.request.Request(
        f"{MSG_SERVER}/msg/send",
        data=json.dumps(data).encode('utf-8'),
        headers={
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {OLLAMA_API_KEY}'
        },
        method='POST'
    )
    
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"code": 500, "error": str(e)}

def recv_message(to="xiaozhi", limit=10, mark_read=True):
    """接收消息"""
    params = {
        "to": to,
        "limit": limit,
        "read": "1" if mark_read else "0",
        "key": OLLAMA_API_KEY
    }
    
    url = f"{MSG_SERVER}/msg/recv?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"code": 500, "error": str(e), "messages": []}

def list_messages(to=None, from_=None, limit=20):
    """列出消息历史"""
    params = {"limit": limit, "key": OLLAMA_API_KEY}
    if to:
        params["to"] = to
    if from_:
        params["from"] = from_
    
    url = f"{MSG_SERVER}/msg/list?{urllib.parse.urlencode(params)}"
    
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        return {"code": 500, "error": str(e), "messages": []}

def check_server():
    """检查服务器状态"""
    try:
        with urllib.request.urlopen(f"{MSG_SERVER}/health", timeout=5) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except:
        return {"code": 500, "status": "offline"}

if __name__ == '__main__':
    import sys
    
    if len(sys.argv) < 2:
        print("用法:")
        print("  python message_client.py send <to> <subject> <body>")
        print("  python message_client.py recv")
        print("  python message_client.py check")
        sys.exit(1)
    
    cmd = sys.argv[1]
    
    if cmd == "check":
        result = check_server()
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif cmd == "send":
        if len(sys.argv) < 5:
            print("用法: python message_client.py send <to> <subject> <body>")
            sys.exit(1)
        result = send_message(sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    
    elif cmd == "recv":
        result = recv_message()
        print(json.dumps(result, indent=2, ensure_ascii=False))