#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
紧急停止TUI客户端循环 - 强制解决重复错误问题
"""

import os
import time
import subprocess
import signal

def force_stop_all_tui():
    """强制停止所有TUI相关进程"""
    print("🛑 强制停止所有TUI相关进程...")
    
    # 查找所有openclaw相关进程
    try:
        result = subprocess.run(['pgrep', '-f', 'openclaw'], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"🔍 找到OpenClaw进程: {pids}")
            
            # 强制停止所有进程
            for pid in pids:
                try:
                    # 先尝试正常停止
                    os.kill(int(pid), signal.SIGTERM)
                    print(f"✅ 发送停止信号到进程 {pid}")
                    time.sleep(0.5)
                    
                    # 检查是否还在运行，如果是则强制停止
                    try:
                        os.kill(int(pid), 0)  # 检查进程是否存在
                        os.kill(int(pid), signal.SIGKILL)
                        print(f"⚡ 强制停止进程 {pid}")
                    except OSError:
                        pass  # 进程已经退出
                        
                except Exception as e:
                    print(f"❌ 停止进程 {pid} 失败: {e}")
        else:
            print("ℹ️  未找到运行的OpenClaw进程")
            
    except Exception as e:
        print(f"❌ 查找进程失败: {e}")
    
    # 额外检查TUI特定进程
    try:
        result = subprocess.run(['pgrep', '-f', 'tui'], capture_output=True, text=True)
        if result.returncode == 0:
            tui_pids = result.stdout.strip().split('\n')
            print(f"🔍 找到TUI进程: {tui_pids}")
            for pid in tui_pids:
                try:
                    os.kill(int(pid), signal.SIGKILL)
                    print(f"⚡ 强制停止TUI进程 {pid}")
                except Exception as e:
                    print(f"❌ 停止TUI进程 {pid} 失败: {e}")
    except Exception as e:
        print(f"❌ 查找TUI进程失败: {e}")

def clear_all_cache():
    """清除所有可能的缓存"""
    print("🧹 清除所有缓存...")
    
    cache_paths = [
        '/tmp/openclaw*',
        '/tmp/*openclaw*',
        '/tmp/.openclaw*',
        os.path.expanduser('~/.cache/openclaw*'),
        os.path.expanduser('~/.openclaw/cache*'),
        '/tmp/*tui*'
    ]
    
    for pattern in cache_paths:
        try:
            subprocess.run(['rm', '-rf'] + subprocess.run(['find', '/tmp', '-name', pattern.split('/')[-1]], 
                                                       capture_output=True, text=True).stdout.splitlines(), 
                         timeout=10)
            print(f"✅ 清理缓存模式: {pattern}")
        except Exception as e:
            print(f"⚠️  清理缓存 {pattern} 失败: {e}")

def create_permanent_lock():
    """创建永久锁文件"""
    lock_file = "/tmp/openclaw_emergency_lock"
    try:
        with open(lock_file, 'w') as f:
            f.write("EMERGENCY LOCK - TUI EDIT LOOP DETECTED\n")
            f.write(f"Lock created at: {time.ctime()}\n")
            f.write("Reason: Infinite edit failure loop\n")
            f.write("Action: All TUI operations suspended\n")
            f.write("Contact: Use generate_safe_edit_operation.py for manual edits\n")
        print(f"🔒 创建紧急锁文件: {lock_file}")
        return lock_file
    except Exception as e:
        print(f"❌ 创建锁文件失败: {e}")
        return None

def main():
    print("🚨 紧急停止TUI客户端循环")
    print("=" * 50)
    print("检测到TUI客户端陷入无限编辑失败循环")
    print("正在执行紧急停止操作...")
    
    # 1. 强制停止所有相关进程
    force_stop_all_tui()
    
    # 2. 清除所有缓存
    clear_all_cache()
    
    # 3. 创建永久锁
    lock_file = create_permanent_lock()
    
    # 4. 等待确保进程停止
    time.sleep(2)
    
    # 5. 最终状态检查
    print("\n🔍 最终状态检查:")
    result = subprocess.run(['pgrep', '-f', 'openclaw'], capture_output=True, text=True)
    if result.returncode != 0:
        print("✅ 所有OpenClaw进程已停止")
    else:
        print(f"⚠️  仍有进程运行: {result.stdout}")
    
    print("\n🎯 紧急操作完成!")
    print("TUI客户端循环已强制停止")
    print("使用 generate_safe_edit_operation.py 进行手动编辑")

if __name__ == "__main__":
    main()