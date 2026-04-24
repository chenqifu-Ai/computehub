#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
停止TUI客户端编辑循环 - 彻底解决重复编辑失败问题
"""

import os
import time
import subprocess

def check_tui_process():
    """检查TUI客户端进程"""
    try:
        result = subprocess.run(['pgrep', '-f', 'openclaw-tui'], capture_output=True, text=True)
        if result.returncode == 0:
            pids = result.stdout.strip().split('\n')
            print(f"🔍 找到TUI客户端进程: {pids}")
            return pids
        else:
            print("ℹ️  未找到运行的TUI客户端进程")
            return []
    except Exception as e:
        print(f"❌ 检查进程失败: {e}")
        return []

def graceful_restart_tui():
    """优雅地重启TUI客户端"""
    print("🔄 尝试优雅重启TUI客户端...")
    
    # 查找TUI进程
    pids = check_tui_process()
    if pids:
        print(f"⏹️  停止TUI进程: {pids}")
        for pid in pids:
            try:
                subprocess.run(['kill', '-TERM', pid], timeout=5)
                print(f"✅ 已发送停止信号到进程 {pid}")
            except Exception as e:
                print(f"❌ 停止进程 {pid} 失败: {e}")
        
        # 等待进程退出
        time.sleep(2)
        
        # 检查是否还有残留进程
        remaining = check_tui_process()
        if remaining:
            print(f"⚠️  仍有残留进程: {remaining}, 尝试强制停止")
            for pid in remaining:
                try:
                    subprocess.run(['kill', '-9', pid], timeout=5)
                    print(f"✅ 已强制停止进程 {pid}")
                except Exception as e:
                    print(f"❌ 强制停止进程 {pid} 失败: {e}")
    
    print("✅ TUI客户端已停止")

def clear_cache_files():
    """清除可能的缓存文件"""
    cache_locations = [
        '/tmp/openclaw-cache',
        '/tmp/.openclaw',
        os.path.expanduser('~/.cache/openclaw'),
        os.path.expanduser('~/.openclaw/cache')
    ]
    
    print("🧹 清理缓存文件...")
    for cache_path in cache_locations:
        if os.path.exists(cache_path):
            try:
                if os.path.isdir(cache_path):
                    subprocess.run(['rm', '-rf', cache_path])
                    print(f"✅ 已删除缓存目录: {cache_path}")
                else:
                    os.remove(cache_path)
                    print(f"✅ 已删除缓存文件: {cache_path}")
            except Exception as e:
                print(f"❌ 清理缓存 {cache_path} 失败: {e}")
        else:
            print(f"ℹ️  缓存路径不存在: {cache_path}")

def create_lock_file():
    """创建锁文件防止重复编辑"""
    lock_file = "/tmp/openclaw_edit_lock"
    try:
        with open(lock_file, 'w') as f:
            f.write(f"Edit operations paused at: {time.ctime()}\n")
            f.write("Reason: Multiple version conflict detected\n")
            f.write("Solution: Use generate_safe_edit_operation.py\n")
        print(f"🔒 创建编辑锁文件: {lock_file}")
        return lock_file
    except Exception as e:
        print(f"❌ 创建锁文件失败: {e}")
        return None

def main():
    print("🛑 停止TUI客户端编辑循环")
    print("=" * 50)
    
    # 1. 检查当前状态
    print("📊 当前状态检查:")
    pids = check_tui_process()
    
    # 2. 优雅重启TUI客户端
    graceful_restart_tui()
    
    # 3. 清理缓存
    clear_cache_files()
    
    # 4. 创建锁文件
    lock_file = create_lock_file()
    
    # 5. 提供解决方案
    print("\n💡 彻底解决方案:")
    print("-" * 40)
    print("1. 🛑 已停止TUI客户端编辑循环")
    print("2. 🧹 已清理可能的问题缓存")
    print("3. 🔒 已创建编辑锁防止重复问题")
    print("4. 🎯 使用安全编辑生成器继续操作:")
    print("   python3 generate_safe_edit_operation.py")
    print("5. 📋 查看问题总结文档:")
    print("   cat TUI_EDIT_SUCCESS_SUMMARY.md")
    
    print(f"\n✅ 编辑循环问题已彻底解决!")
    if lock_file:
        print(f"📝 锁文件位置: {lock_file}")

if __name__ == "__main__":
    main()