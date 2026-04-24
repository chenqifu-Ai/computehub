#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
茶信快速客户端 - 局域网优先，云端备用
"""

import json
import urllib.request
import time

# 配置
API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"

# 节点地址（局域网优先）
NODES = {
    "hongcha": ["http://192.168.1.3:8080", "https://ntfy.sh/chaxin-chat-hongcha"],
    "xiaozhi": ["http://192.168.1.17:8080", "https://ntfy.sh/chaxin-chat-xiaozhi"]
}

def send_message(to, subject="", body="", from_="xiaozhi"):
    """发送消息 - 局域网优先"""
    if to not in NODES:
        return {"error": f"Unknown node: {to}"}
    
    msg = {
        "id": f"msg_{int(time.time()*1000)}_{from_}",
        "from": from_,
        "to": to,
        "subject": subject,
        "body": body,
        "timestamp": time.time()
    }
    
    # 先尝试局域网
    for url in NODES[to]:
        try:
            if url.startswith("http://192"):
                # 局域网直连
                api_url = f"{url}/msg/send?key={API_KEY}"
                req = urllib.request.Request(
                    api_url,
                    data=json.dumps(msg, ensure_ascii=False).encode('utf-8'),
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=5) as resp:
                    return {"status": "sent", "method": "lan", "msg_id": msg["id"]}
            else:
                # 云端中转
                req = urllib.request.Request(
                    url,
                    data=json.dumps(msg, ensure_ascii=False).encode('utf-8'),
                    headers={'Content-Type': 'application/json'},
                    method='POST'
                )
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return {"status": "sent", "method": "cloud", "msg_id": msg["id"]}
        except Exception as e:
            continue
    
    return {"error": "All nodes failed"}

def recv_messages(to, limit=10):
    """接收消息"""
    if to not in NODES:
        return {"error": f"Unknown node: {to}"}
    
    for url in NODES[to]:
        try:
            if url.startswith("http://192"):
                api_url = f"{url}/msg/list?key={API_KEY}&to={to}&limit={limit}"
                req = urllib.request.Request(api_url)
                with urllib.request.urlopen(req, timeout=5) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    data["method"] = "lan"
                    return data
        except:
            continue
    
    return {"error": "All nodes failed"}

if __name__ == '__main__':
    import sys
    if len(sys.argv) < 2:
        print("用法: python fast_client.py send <to> <subject> <body>")
        print("用法: python fast_client.py recv <to>")
        sys.exit(1)
    
    cmd = sys.argv[1]
    if cmd == "send" and len(sys.argv) >= 5:
        result = send_message(sys.argv[2], sys.argv[3], sys.argv[4])
        print(json.dumps(result, indent=2, ensure_ascii=False))
    elif cmd == "recv":
        to = sys.argv[2] if len(sys.argv) > 2 else "xiaozhi"
        result = recv_messages(to)
        print(json.dumps(result, indent=2, ensure_ascii=False))
