#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Ollama 模型拉取监控器
实时监控模型下载进度和速度
"""

import requests
import time
import sys
from datetime import datetime

SERVER_URL = "http://192.168.2.165:11434"
MODEL_NAME = "ministral-3:14b"

def format_size(bytes_val):
    """格式化字节大小为人类可读格式"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if abs(bytes_val) < 1024.0:
            return f"{bytes_val:.2f} {unit}"
        bytes_val /= 1024.0
    return f"{bytes_val:.2f} TB"

def format_speed(bytes_per_sec):
    """格式化速度"""
    return f"{format_size(bytes_per_sec)}/s"

def monitor_pull():
    """监控模型拉取进度"""
    print("=" * 70)
    print(f"📥 Ollama 模型拉取监控")
    print(f"   服务器：{SERVER_URL}")
    print(f"   模型：{MODEL_NAME}")
    print("=" * 70)
    print()
    
    last_completed = 0
    last_time = time.time()
    total = 0
    status = "waiting"
    
    try:
        # 启动拉取请求（流式）
        response = requests.post(
            f"{SERVER_URL}/api/pull",
            json={"name": MODEL_NAME},
            stream=True,
            timeout=300
        )
        
        for line in response.iter_lines():
            if line:
                try:
                    data = line.decode('utf-8')
                    if 'status' in data:
                        import json
                        obj = json.loads(data)
                        status = obj.get('status', 'unknown')
                        
                        if 'total' in obj and 'completed' in obj:
                            total = obj['total']
                            completed = obj['completed']
                            progress = (completed / total * 100) if total > 0 else 0
                            
                            # 计算速度
                            current_time = time.time()
                            time_diff = current_time - last_time
                            size_diff = completed - last_completed
                            
                            if time_diff > 0:
                                speed = size_diff / time_diff
                            else:
                                speed = 0
                            
                            # 估算剩余时间
                            if speed > 0:
                                remaining = (total - completed) / speed
                                eta = datetime.now().timestamp() + remaining
                                eta_str = datetime.fromtimestamp(eta).strftime('%H:%M:%S')
                            else:
                                eta_str = "未知"
                            
                            # 打印进度
                            bar_len = 40
                            filled = int(bar_len * progress / 100)
                            bar = "█" * filled + "░" * (bar_len - filled)
                            
                            print(f"\r[{status}] |{bar}| {progress:5.1f}% | "
                                  f"{format_size(completed)}/{format_size(total)} | "
                                  f"速度：{format_speed(speed)} | "
                                  f"预计：{eta_str}", 
                                  end='', flush=True)
                            
                            last_completed = completed
                            last_time = current_time
                            
                        elif status == 'success':
                            print(f"\n\n✅ 模型拉取成功!")
                            print(f"   模型：{MODEL_NAME}")
                            print(f"   服务器：{SERVER_URL}")
                            print(f"   完成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            return True
                        elif status in ['verifying', 'downloading', 'pulling manifest']:
                            print(f"\r[{status}] 处理中...", end='', flush=True)
                            
                except Exception as e:
                    pass
                    
    except KeyboardInterrupt:
        print("\n\n⚠️  用户中断")
        return False
    except Exception as e:
        print(f"\n\n❌ 错误：{e}")
        return False
    
    print("\n\n⚠️  拉取完成")
    return True

if __name__ == '__main__':
    success = monitor_pull()
    sys.exit(0 if success else 1)
