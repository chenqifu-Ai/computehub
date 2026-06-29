#!/usr/bin/env python3
"""
ARC-AI-NET-002: AI间消息自动消费 + 自动回复
===========================================
Phase 1: Worker 收到 Base64 ARC-AI-NET-001 消息时，自动解码并触发 Agent think 回复
Phase 2: 多节点消息路由（ecs-p2ph ↔ windows-mobile ↔ localhost）
Phase 3: 消息回执、超时、重试

标准: ARC-AI-NET-002
"""

# 等会改为 Go 实现嵌入 computehub worker，先用 Python 原型验证逻辑

import base64, json, urllib.request, time, os

API = 'http://36.250.122.43:8282'
HEADERS = {'Content-Type': 'application/json'}

def submit_task(node_id, command, source_type='api', timeout=60):
    """提交任务到 Gateway"""
    tid = f'ai-auto-{int(time.time()*1000)}'
    task = {
        'task_id': tid,
        'node_id': node_id,
        'command': command,
        'timeout': timeout,
        'source_type': source_type
    }
    req = urllib.request.Request(f'{API}/api/v1/tasks/submit',
                                 data=json.dumps(task).encode(),
                                 headers=HEADERS)
    try:
        resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
        return resp.get('success', False), tid
    except Exception as e:
        return False, str(e)

def get_pending_messages(node_id):
    """获取某节点上待处理的 AI 消息"""
    req = urllib.request.Request(f'{API}/api/v1/tasks/list')
    resp = json.loads(urllib.request.urlopen(req, timeout=10).read().decode())
    pending = []
    for t in resp['data'].get(node_id, []):
        cmd = t.get('command', '')
        if not cmd:
            continue
        try:
            decoded = json.loads(base64.b64decode(cmd).decode())
            if decoded.get('protocol') == 'arc-ai-net-001':
                if decoded.get('to') == '小智B' or decoded.get('to') == '小智A':
                    # 检查是否已经回复过
                    # 简单策略：如果 from/to 都有且 content 存在，就是新消息
                    pending.append({
                        'task_id': t['task_id'],
                        'msg': decoded,
                        'status': t['status']
                    })
        except:
            pass
    return pending

def auto_consume_loop():
    """自动消费循环：检查队列 → 触发 Agent think → 发回"""
    print('🤖 ARC-AI-NET-002 自动消费循环启动...')
    
    checked_msgs = set()
    
    while True:
        try:
            # 检查 ecs-p2ph 的消息
            msgs = get_pending_messages('ecs-p2ph')
            for m in msgs:
                msg_id = m['msg'].get('msg_id', '')
                if msg_id in checked_msgs:
                    continue
                checked_msgs.add(msg_id)
                
                frm = m['msg'].get('from', '')
                to = m['msg'].get('to', '')
                content = m['msg'].get('content', '')[:100]
                
                print(f'\n📩 新消息: {frm} → {to}')
                print(f'   内容: {content}')
                
                # 触发 Agent think 处理这条消息
                think_prompt = f"你收到一条来自{frm}的ARC-AI-NET-001消息：{m['msg'].get('content','')}。请思考并回复。使用ai_send工具发送回复。"
                
                success, tid = submit_task('ecs-p2ph', think_prompt, source_type='agent')
                if success:
                    print(f'   ✅ 已触发 Agent think: {tid}')
                else:
                    print(f'   ❌ 触发失败: {tid}')
            
        except Exception as e:
            print(f'⚠️ 轮询错误: {e}')
        
        time.sleep(10)  # 每10秒检查一次

if __name__ == '__main__':
    auto_consume_loop()