#!/usr/bin/env python3
"""
异常进程监控系统
实时监控系统进程，检测异常行为并报警
"""

import subprocess
import json
import time
import os
from datetime import datetime
import psutil

class ProcessMonitor:
    def __init__(self):
        self.known_processes = self._load_known_processes()
        self.suspicious_patterns = [
            'miner', 'backdoor', 'reverse_shell', 'keylogger',
            'crypto', 'ransom', 'botnet', 'trojan', 'worm',
            'rootkit', 'spyware', 'adware', 'malware',
            'hidden', 'stealth', 'obfuscated', 'packed'
        ]
        
    def _load_known_processes(self):
        """加载已知的正常进程列表"""
        known = {
            # 系统进程
            'systemd', 'init', 'kthreadd', 'ksoftirqd', 'rcu_sched',
            'migration', 'watchdog', 'cpuhp', 'kworker', 'irq',
            
            # 常用服务
            'sshd', 'nginx', 'apache', 'mysql', 'postgres',
            'redis', 'mongod', 'docker', 'containerd',
            
            # 开发工具
            'python', 'node', 'java', 'bash', 'zsh', 'fish',
            'vim', 'nano', 'emacs', 'git', 'adb',
            
            # OpenClaw相关
            'openclaw', 'node', 'npm', 'yarn',
            
            # 网络工具
            'curl', 'wget', 'ping', 'ssh', 'scp',
            
            # 系统工具
            'top', 'htop', 'ps', 'ls', 'cat', 'grep',
            'find', 'awk', 'sed', 'cut', 'sort', 'uniq'
        }
        return known
    
    def get_running_processes(self):
        """获取当前运行的所有进程"""
        processes = []
        for proc in psutil.process_iter(['pid', 'name', 'username', 'cmdline', 'create_time']):
            try:
                process_info = proc.info
                processes.append(process_info)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return processes
    
    def analyze_process(self, process):
        """分析单个进程的异常特征"""
        risk_level = 0
        alerts = []
        
        pid = process.get('pid')
        name = process.get('name', '').lower()
        cmdline = ' '.join(process.get('cmdline', []) or []).lower()
        username = process.get('username', '')
        
        # 检查已知进程
        if name not in self.known_processes and not any(k in name for k in self.known_processes):
            risk_level += 1
            alerts.append(f"未知进程: {name}")
        
        # 检查可疑模式
        for pattern in self.suspicious_patterns:
            if pattern in name or pattern in cmdline:
                risk_level += 2
                alerts.append(f"可疑模式: {pattern}")
        
        # 检查异常用户
        if username not in ['root', 'u0_a355', 'u0_a207', 'u0_a46'] and not username.startswith('u0_a'):
            risk_level += 1
            alerts.append(f"异常用户: {username}")
        
        # 检查隐藏进程（无cmdline）
        if not cmdline.strip() and name != 'kthreadd':
            risk_level += 1
            alerts.append("隐藏进程（无命令行）")
        
        return {
            'pid': pid,
            'name': name,
            'username': username,
            'cmdline': cmdline[:200],  # 截断长命令行
            'risk_level': risk_level,
            'alerts': alerts,
            'timestamp': datetime.now().isoformat()
        }
    
    def monitor(self, interval=60):
        """持续监控进程"""
        print(f"🚀 启动异常进程监控系统 (间隔: {interval}秒)")
        print(f"📊 已知正常进程数: {len(self.known_processes)}")
        print(f"🔍 监控模式: {len(self.suspicious_patterns)} 个可疑模式")
        print("-" * 50)
        
        while True:
            try:
                processes = self.get_running_processes()
                suspicious_count = 0
                
                print(f"\n🕐 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                print(f"📈 总进程数: {len(processes)}")
                
                for process in processes:
                    analysis = self.analyze_process(process)
                    
                    if analysis['risk_level'] > 0:
                        suspicious_count += 1
                        print(f"\n⚠️  可疑进程 detected!")
                        print(f"   PID: {analysis['pid']}")
                        print(f"   名称: {analysis['name']}")
                        print(f"   用户: {analysis['username']}")
                        print(f"   风险等级: {analysis['risk_level']}/5")
                        print(f"   警报: {', '.join(analysis['alerts'])}")
                        print(f"   命令行: {analysis['cmdline']}")
                
                if suspicious_count == 0:
                    print("✅ 未发现可疑进程")
                else:
                    print(f"\n🔴 发现 {suspicious_count} 个可疑进程!")
                
                # 保存监控日志
                self.save_log(processes, suspicious_count)
                
                time.sleep(interval)
                
            except KeyboardInterrupt:
                print("\n🛑 监控已停止")
                break
            except Exception as e:
                print(f"❌ 监控错误: {e}")
                time.sleep(interval)
    
    def save_log(self, processes, suspicious_count):
        """保存监控日志"""
        log_dir = "/root/.openclaw/workspace/logs/process_monitor"
        os.makedirs(log_dir, exist_ok=True)
        
        log_file = os.path.join(log_dir, f"monitor_{datetime.now().strftime('%Y%m%d')}.log")
        
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'total_processes': len(processes),
            'suspicious_count': suspicious_count,
            'status': 'NORMAL' if suspicious_count == 0 else 'WARNING'
        }
        
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

def main():
    """主函数"""
    monitor = ProcessMonitor()
    
    # 立即运行一次检查
    print("🔍 立即执行一次进程检查...")
    processes = monitor.get_running_processes()
    
    suspicious_processes = []
    for process in processes:
        analysis = monitor.analyze_process(process)
        if analysis['risk_level'] > 0:
            suspicious_processes.append(analysis)
    
    print(f"\n📊 当前系统状态:")
    print(f"   总进程数: {len(processes)}")
    print(f"   可疑进程数: {len(suspicious_processes)}")
    
    if suspicious_processes:
        print(f"\n🔴 发现可疑进程:")
        for proc in suspicious_processes:
            print(f"   PID {proc['pid']}: {proc['name']} (风险: {proc['risk_level']}) - {', '.join(proc['alerts'])}")
    else:
        print("✅ 系统干净，未发现可疑进程")
    
    # 开始持续监控
    print(f"\n🚀 启动持续监控 (60秒间隔)...")
    monitor.monitor(interval=60)

if __name__ == "__main__":
    main()