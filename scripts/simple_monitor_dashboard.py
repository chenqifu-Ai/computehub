#!/usr/bin/env python3
"""
简化版进程监控驾驶舱 - 只显示核心信息
"""

import json
import time
import subprocess
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

class SimpleProcessMonitorDashboard:
    def __init__(self, port=8081):
        self.port = port
        self.known_processes = self._load_known_processes()
    
    def _load_known_processes(self):
        return [
            "systemd", "init", "kthreadd", "ksoftirqd", "rcu_sched",
            "sshd", "bash", "python", "node", "java", "nginx", "apache",
            "mysql", "redis", "docker", "containerd", "openclaw",
            "adb", "curl", "wget", "ssh", "scp", "top", "htop", "ps",
            "grep", "awk", "sed", "find", "cat", "ls", "proot"
        ]
    
    def get_process_data(self):
        """获取进程数据"""
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
            
            processes = []
            suspicious_count = 0
            
            for line in lines:
                parts = line.split()
                if len(parts) < 11:
                    continue
                    
                pid = parts[1]
                user = parts[0]
                cpu = parts[2]
                mem = parts[3]
                cmd = ' '.join(parts[10:])
                
                # 风险等级评估
                risk_level = 0
                alerts = []
                
                # 检查未知进程
                is_known = any(known in cmd.lower() for known in self.known_processes)
                if not is_known:
                    risk_level = 1
                    alerts.append("未知进程")
                
                if risk_level > 0:
                    suspicious_count += 1
                    processes.append({
                        'pid': pid,
                        'user': user,
                        'cpu': cpu,
                        'mem': mem,
                        'cmd': cmd[:100] + ('...' if len(cmd) > 100 else ''),
                        'risk_level': risk_level,
                        'alerts': alerts
                    })
            
            return {
                'total_processes': len(lines),
                'suspicious_count': suspicious_count,
                'processes': processes,
                'status': 'NORMAL' if suspicious_count == 0 else 'WARNING',
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {
                'total_processes': 0,
                'suspicious_count': 0,
                'processes': [],
                'status': 'ERROR',
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def generate_html(self, data):
        """生成简化版HTML"""
        status_color = "green" if data['status'] == 'NORMAL' else "red"
        status_emoji = "✅" if data['status'] == 'NORMAL' else "🔴"
        
        processes_html = ""
        for proc in data['processes']:
            row_color = "#ffebee" if proc['risk_level'] >= 2 else "#fff3e0"
            processes_html += f"""
            <tr style="background-color: {row_color};">
                <td>{proc['pid']}</td>
                <td>{proc['user']}</td>
                <td>{proc['cpu']}%</td>
                <td>{proc['mem']}%</td>
                <td>{proc['cmd']}</td>
                <td>{proc['risk_level']}</td>
                <td>{', '.join(proc['alerts'])}</td>
            </tr>
            """
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>🛡️ 进程监控驾驶舱</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .dashboard {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .status {{ font-size: 24px; font-weight: bold; color: {status_color}; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; flex: 1; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        .danger {{ background-color: #ffebee; }}
        .warning {{ background-color: #fff3e0; }}
    </style>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <div class="dashboard">
        <h1>🛡️ 进程监控驾驶舱</h1>
        
        <div class="status">
            {status_emoji} 系统状态: {data['status']}
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>📊 总进程数</h3>
                <p style="font-size: 24px; margin: 0;">{data['total_processes']}</p>
            </div>
            <div class="stat-card">
                <h3>⚠️ 可疑进程</h3>
                <p style="font-size: 24px; margin: 0; color: {'red' if data['suspicious_count'] > 0 else 'green'};">
                    {data['suspicious_count']}
                </p>
            </div>
            <div class="stat-card">
                <h3>🕐 最后更新</h3>
                <p style="font-size: 14px; margin: 0;">{data['last_update']}</p>
            </div>
        </div>
        
        <h2>🔍 可疑进程列表</h2>
        <table>
            <tr>
                <th>PID</th>
                <th>用户</th>
                <th>CPU%</th>
                <th>内存%</th>
                <th>命令行</th>
                <th>风险等级</th>
                <th>警报信息</th>
            </tr>
            {processes_html}
        </table>
        
        <div style="margin-top: 20px; color: #666; font-size: 12px;">
            <div id="countdown" style="font-size: 16px; font-weight: bold; color: #007bff; margin-bottom: 5px;">
                ⏰ 倒计时: <span id="timer">30</span>秒
            </div>
            <div style="margin-top: 10px;">
                <a href="/detailed" style="color: #007bff; text-decoration: none; font-weight: bold;">
                    📋 点击查看完整进程列表 (共{data['total_processes']}个进程)
                </a>
            </div>
            页面每30秒自动刷新 | 简化版监控系统
        </div>
        
        <script>
            let seconds = 30;
            const timerElement = document.getElementById('timer');
            
            function updateCountdown() {{
                seconds--;
                timerElement.textContent = seconds;
                
                if (seconds <= 0) {{
                    seconds = 30;
                    location.reload();
                }}
            }}
            
            setInterval(updateCountdown, 1000);
        </script>
    </div>
</body>
</html>
"""

class SimpleDashboardHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.dashboard = SimpleProcessMonitorDashboard()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            data = self.dashboard.get_process_data()
            html = self.dashboard.generate_html(data)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def run_server():
    server = HTTPServer(('0.0.0.0', 8081), SimpleDashboardHandler)
    print("🚀 简化版进程监控驾驶舱启动在 http://localhost:8081")
    print("📊 只显示核心信息，不显示监控规则详情")
    server.serve_forever()

if __name__ == "__main__":
    run_server()