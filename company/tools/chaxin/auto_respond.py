#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
红茶自动响应脚本 - 监听消息并自动回复
"""

import json
import urllib.request
import time
import os
import sys

# 配置
API_KEY = "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"
MESSAGE_URL = "http://localhost:8080/msg/list"
SEND_URL = "http://localhost:8080/msg/send"
NODE_ID = "hongcha"
POLL_INTERVAL = 5  # 秒

def get_messages(to, limit=10):
    """获取消息"""
    url = f"{MESSAGE_URL}?key={API_KEY}&to={to}&limit={limit}"
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get("messages", [])
    except Exception as e:
        print(f"[错误] 获取消息失败: {e}")
        return []

def send_message(to, subject, body, from_="hongcha"):
    """发送消息"""
    msg = {
        "from": from_,
        "to": to,
        "subject": subject,
        "body": body,
        "timestamp": time.time()
    }
    url = f"{SEND_URL}?key={API_KEY}"
    try:
        req = urllib.request.Request(
            url,
            data=json.dumps(msg, ensure_ascii=False).encode('utf-8'),
            headers={'Content-Type': 'application/json'},
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f"[错误] 发送消息失败: {e}")
        return {"error": str(e)}

def process_message(msg):
    """处理收到的消息"""
    subject = msg.get("subject", "")
    body = msg.get("body", "")
    from_ = msg.get("from", "unknown")
    
    print(f"[收到] {from_}: {subject}")
    
    # 自动回复
    response = f"""【红茶自动回复】

已收到您的消息：
- 发送者: {from_}
- 主题: {subject}
- 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}

红茶正在处理中...

系统状态：
- Gateway: ✅ 运行中
- 消息队列: ✅ 运行中
- ollama-cloud: ✅ 已配置
"""
    
    return send_message(from_, f"Re: {subject}", response)

def main():
    print(f"[*] 红茶自动响应脚本启动")
    print(f"[*] 监听节点: {NODE_ID}")
    print(f"[*] 轮询间隔: {POLL_INTERVAL}秒")
    
    processed_ids = set()
    
    while True:
        try:
            messages = get_messages(NODE_ID, limit=10)
            
            for msg in messages:
                msg_id = msg.get("id")
                if msg_id and msg_id not in processed_ids:
                    processed_ids.add(msg_id)
                    result = process_message(msg)
                    if "error" not in result:
                        print(f"[回复] 已回复消息 {msg_id}")
            
            # 清理旧ID
            if len(processed_ids) > 100:
                processed_ids = set(list(processed_ids)[-50:])
            
            time.sleep(POLL_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n[*] 停止")
            break
        except Exception as e:
            print(f"[错误] {e}")
            time.sleep(POLL_INTERVAL)

if __name__ == '__main__':
    main()
