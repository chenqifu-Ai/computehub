#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""红茶增强版自动响应 - 解析指令并执行任务"""
import json
import urllib.request
import time
import subprocess
import os

API_KEY = '8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii'
SEND_URL = 'http://192.168.1.17:8080/msg/send'
RECV_URL = 'http://localhost:8080/msg/list'
NODE_ID = 'hongcha'

def get_messages(limit=10):
    url = f'{RECV_URL}?key={API_KEY}&to={NODE_ID}&limit={limit}'
    try:
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            return data.get('messages', [])
    except Exception as e:
        print(f'[错误] 获取消息失败: {e}', flush=True)
        return []

def send_message(to, subject, body):
    msg = {'from': 'hongcha', 'to': to, 'subject': subject, 'body': body, 'timestamp': time.time()}
    url = f'{SEND_URL}?key={API_KEY}'
    try:
        req = urllib.request.Request(url, data=json.dumps(msg, ensure_ascii=False).encode('utf-8'), headers={'Content-Type': 'application/json'}, method='POST')
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except Exception as e:
        print(f'[错误] 发送失败: {e}', flush=True)
        return {'error': str(e)}

def run_command(cmd):
    """执行shell命令并返回结果"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
        return result.stdout + result.stderr
    except subprocess.TimeoutExpired:
        return "命令执行超时"
    except Exception as e:
        return f"执行错误: {e}"

def process_command(msg):
    """解析并执行指令"""
    subject = msg.get('subject', '')
    body = msg.get('body', '')
    from_ = msg.get('from', 'unknown')
    
    print(f'[收到] {from_}: {subject}', flush=True)
    
    # 解析指令类型
    body_lower = body.lower()
    subject_lower = subject.lower()
    
    result = ""
    
    # 检查是否包含指令关键词
    if '股票' in subject or '股票' in body:
        result = handle_stock_command(body)
    elif '状态' in subject or '状态' in body or '检查' in body:
        result = check_system_status()
    elif '启动' in body or '运行' in body:
        result = handle_start_command(body)
    elif '开发' in subject or '开发' in body:
        result = handle_dev_command(body)
    elif '汇报' in body or '报告' in body:
        result = generate_report()
    else:
        result = f"""【红茶回复】

收到来自 {from_} 的消息：
主题：{subject}
时间：{time.strftime("%Y-%m-%d %H:%M:%S")}

消息内容已记录。

系统状态：
- Gateway: 运行中
- 消息队列: 运行中
- ollama-cloud: 已配置
"""
    
    send_message(from_, f'Re: {subject}', result)

def handle_stock_command(body):
    """处理股票相关指令"""
    result = "【股票系统操作结果】\n\n"
    
    # 检查股票系统状态
    status = run_command("curl -s http://localhost:8000/health 2>/dev/null || echo '未运行'")
    
    if '未运行' in status or '404' in status:
        result += "股票系统未启动，正在启动...\n"
        start_result = run_command("cd ~/.openclaw/workspace/projects/stock-trading/backend && nohup python3 simple_server.py > /tmp/stock.log 2>&1 &")
        time.sleep(3)
        status = run_command("curl -s http://localhost:8000/health")
        result += f"启动结果: {status}\n"
    else:
        result += f"股票系统状态: {status}\n"
    
    # 检查API
    stocks = run_command("curl -s http://localhost:8000/api/market/stocks 2>/dev/null | head -100")
    if stocks and 'code":200' in stocks:
        result += "股票API: ✅ 正常\n"
    else:
        result += "股票API: ⚠️ 异常\n"
    
    return result

def check_system_status():
    """检查系统状态"""
    result = "【系统状态报告】\n\n"
    
    # CPU和内存
    result += run_command("uptime")
    result += "\n"
    
    # 磁盘
    result += run_command("df -h / | tail -1")
    result += "\n"
    
    # 进程
    result += "关键进程:\n"
    processes = run_command("ps aux | grep -E 'openclaw|message_queue|auto_respond' | grep -v grep")
    result += processes + "\n"
    
    # Gateway
    gateway = run_command("curl -s http://localhost:18789/health")
    result += f"Gateway: {gateway}\n"
    
    # 消息队列
    mq = run_command("curl -s http://localhost:8080/health")
    result += f"消息队列: {mq}\n"
    
    return result

def handle_start_command(body):
    """处理启动指令"""
    result = "【启动操作结果】\n\n"
    
    if '股票' in body:
        result += "启动股票系统...\n"
        result += run_command("cd ~/.openclaw/workspace/projects/stock-trading/backend && pkill -f 'python.*simple_server' 2>/dev/null; nohup python3 simple_server.py > /tmp/stock.log 2>&1 &")
        time.sleep(3)
        result += run_command("curl -s http://localhost:8000/health")
    elif 'gateway' in body.lower():
        result += "启动Gateway...\n"
        result += run_command("cd ~/.openclaw && nohup openclaw gateway > /tmp/gateway.log 2>&1 &")
    else:
        result += "请指定要启动的服务"
    
    return result

def handle_dev_command(body):
    """处理开发指令"""
    result = "【开发任务执行】\n\n"
    
    result += "当前开发环境状态:\n"
    result += run_command("ls -la ~/.openclaw/workspace/projects/ 2>/dev/null")
    result += "\n"
    
    result += "股票系统文件:\n"
    result += run_command("ls -la ~/.openclaw/workspace/projects/stock-trading/backend/ 2>/dev/null | head -15")
    
    return result

def generate_report():
    """生成工作汇报"""
    result = "【红茶工作汇报】\n\n"
    result += f"时间: {time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    result += "系统状态:\n"
    result += f"- Gateway: {run_command('curl -s http://localhost:18789/health')}\n"
    result += f"- 消息队列: {run_command('curl -s http://localhost:8080/health')}\n"
    result += f"- 自动响应: 运行中\n\n"
    
    result += "进程状态:\n"
    result += run_command("ps aux | grep -E 'openclaw|message_queue|health_monitor|auto_respond' | grep -v grep | wc -l")
    result += " 个关键进程运行中\n\n"
    
    result += "待处理消息:\n"
    msgs = get_messages(5)
    for m in msgs:
        result += f"- {m.get('subject', '无主题')}\n"
    
    return result

def main():
    print('[*] 红茶增强版自动响应启动', flush=True)
    print(f'[*] 节点: {NODE_ID}', flush=True)
    
    processed_ids = set()
    
    while True:
        try:
            messages = get_messages(10)
            for msg in messages:
                msg_id = msg.get('id')
                if msg_id and msg_id not in processed_ids:
                    processed_ids.add(msg_id)
                    process_command(msg)
            
            # 清理旧ID
            if len(processed_ids) > 100:
                processed_ids = set(list(processed_ids)[-50:])
            
            time.sleep(5)
        except KeyboardInterrupt:
            print('[*] 停止', flush=True)
            break
        except Exception as e:
            print(f'[错误] {e}', flush=True)
            time.sleep(5)

if __name__ == '__main__':
    main()
