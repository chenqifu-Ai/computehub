#!/usr/bin/env python3
"""
增强版图形界面进程监控 - 带CPU/内存监控和停止按钮
"""

import subprocess
import time
import psutil
from http.server import HTTPServer, BaseHTTPRequestHandler

class EnhancedGUIProcessMonitor:
    def get_processes(self):
        """获取进程列表"""
        try:
            result = subprocess.run(['ps', 'aux'], capture_output=True, text=True)
            lines = result.stdout.strip().split('\n')[1:]  # 跳过标题行
            
            processes = []
            for line in lines:
                parts = line.split()
                if len(parts) < 11:
                    continue
                    
                pid = parts[1]
                user = parts[0]
                cpu = parts[2]
                mem = parts[3]
                cmd = ' '.join(parts[10:])
                
                processes.append({
                    'pid': pid,
                    'user': user,
                    'cpu': cpu,
                    'mem': mem,
                    'cmd': cmd[:50] + ('...' if len(cmd) > 50 else ''),
                    'full_cmd': cmd
                })
            
            return processes
            
        except Exception as e:
            return []
    
    def get_system_stats(self):
        """获取系统CPU和内存使用情况"""
        try:
            # CPU使用率
            cpu_percent = psutil.cpu_percent(interval=1)
            
            # 内存使用情况
            memory = psutil.virtual_memory()
            mem_total = memory.total / (1024 * 1024)  # MB
            mem_used = memory.used / (1024 * 1024)    # MB
            mem_percent = memory.percent
            
            # 磁盘使用情况
            disk = psutil.disk_usage('/')
            disk_total = disk.total / (1024 * 1024 * 1024)  # GB
            disk_used = disk.used / (1024 * 1024 * 1024)    # GB
            disk_percent = disk.percent
            
            # 网络信息
            net_io = psutil.net_io_counters()
            bytes_sent = net_io.bytes_sent / (1024 * 1024)  # MB
            bytes_recv = net_io.bytes_recv / (1024 * 1024)  # MB
            
            return {
                'cpu_percent': cpu_percent,
                'mem_total': round(mem_total, 1),
                'mem_used': round(mem_used, 1),
                'mem_percent': mem_percent,
                'disk_total': round(disk_total, 1),
                'disk_used': round(disk_used, 1),
                'disk_percent': disk_percent,
                'bytes_sent': round(bytes_sent, 1),
                'bytes_recv': round(bytes_recv, 1)
            }
            
        except Exception as e:
            return {
                'cpu_percent': 0,
                'mem_total': 0,
                'mem_used': 0,
                'mem_percent': 0,
                'disk_total': 0,
                'disk_used': 0,
                'disk_percent': 0,
                'bytes_sent': 0,
                'bytes_recv': 0
            }
    
    def kill_process(self, pid):
        """停止进程"""
        try:
            result = subprocess.run(['kill', '-9', pid], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

class EnhancedGUIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.monitor = EnhancedGUIProcessMonitor()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            processes = self.monitor.get_processes()
            system_stats = self.monitor.get_system_stats()
            html = self._generate_html(processes, system_stats)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/kill':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            
            # 简单解析PID
            if 'pid=' in post_data:
                pid = post_data.split('pid=')[1].split('&')[0]
                if pid.isdigit():
                    success = self.monitor.kill_process(pid)
            
            # 重定向回主页
            self.send_response(303)
            self.send_header('Location', '/')
            self.end_headers()
    
    def _generate_html(self, processes, system_stats):
        processes_html = ""
        for proc in processes:
            processes_html += f"""
            <tr>
                <td>{proc['pid']}</td>
                <td>{proc['user']}</td>
                <td>{proc['cpu']}%</td>
                <td>{proc['mem']}%</td>
                <td title="{proc['full_cmd']}">{proc['cmd']}</td>
                <td>
                    <form action="/kill" method="post" style="display:inline;">
                        <input type="hidden" name="pid" value="{proc['pid']}">
                        <button type="submit" style="
                            background: #dc3545;
                            color: white;
                            border: none;
                            padding: 5px 12px;
                            border-radius: 4px;
                            cursor: pointer;
                            font-size: 12px;
                        ">⛔ 停止</button>
                    </form>
                </td>
            </tr>
            """
        
        # 系统状态卡片
        cpu_color = "#28a745" if system_stats['cpu_percent'] < 70 else "#ffc107" if system_stats['cpu_percent'] < 90 else "#dc3545"
        mem_color = "#28a745" if system_stats['mem_percent'] < 70 else "#ffc107" if system_stats['mem_percent'] < 90 else "#dc3545"
        disk_color = "#28a745" if system_stats['disk_percent'] < 70 else "#ffc107" if system_stats['disk_percent'] < 90 else "#dc3545"
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>🖥️ 增强版系统监控</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 20px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
        }}
        .container {{
            max-width: 1400px;
            margin: 0 auto;
            background: white;
            padding: 30px;
            border-radius: 15px;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            color: #333;
        }}
        .header h1 {{
            font-size: 2.5em;
            margin: 0;
            color: #4a5568;
        }}
        .stats {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
            gap: 20px;
            margin-bottom: 30px;
        }}
        .stat-card {{
            background: #f7fafc;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            color: #4a5568;
            font-size: 1.1em;
        }}
        .stat-card p {{
            font-size: 1.8em;
            margin: 0;
            color: #2d3748;
            font-weight: bold;
        }}
        .progress-bar {{
            background: #e2e8f0;
            height: 20px;
            border-radius: 10px;
            margin: 10px 0;
            overflow: hidden;
        }}
        .progress-fill {{
            height: 100%;
            border-radius: 10px;
            transition: width 0.3s ease;
        }}
        .cpu-progress {{ background: {cpu_color}; }}
        .mem-progress {{ background: {mem_color}; }}
        .disk-progress {{ background: {disk_color}; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: white;
            border-radius: 10px;
            overflow: hidden;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        th, td {{
            padding: 15px;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }}
        th {{
            background: #4a5568;
            color: white;
            font-weight: bold;
            font-size: 1.1em;
        }}
        tr:hover {{
            background: #f7fafc;
        }}
        .warning {{
            color: #e53e3e;
            font-weight: bold;
        }}
        .refresh {{
            text-align: center;
            margin-top: 20px;
            color: #718096;
            font-size: 0.9em;
        }}
        button:hover {{
            background: #c53030 !important;
            transform: translateY(-1px);
        }}
        .network-stats {{
            display: flex;
            justify-content: space-around;
            margin: 10px 0;
        }}
        .network-item {{
            text-align: center;
        }}
        .network-label {{
            font-size: 0.9em;
            color: #718096;
        }}
        .network-value {{
            font-size: 1.2em;
            font-weight: bold;
            color: #4a5568;
        }}
    </style>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖥️ 增强版系统监控面板</h1>
            <p>实时监控CPU、内存、磁盘、网络和进程状态</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>💻 CPU使用率</h3>
                <p style="color: {cpu_color};">{system_stats['cpu_percent']}%</p>
                <div class="progress-bar">
                    <div class="progress-fill cpu-progress" style="width: {system_stats['cpu_percent']}%;"></div>
                </div>
            </div>
            
            <div class="stat-card">
                <h3>🧠 内存使用</h3>
                <p style="color: {mem_color};">{system_stats['mem_percent']}%</p>
                <div class="progress-bar">
                    <div class="progress-fill mem-progress" style="width: {system_stats['mem_percent']}%;"></div>
                </div>
                <div style="font-size: 0.9em; color: #718096;">
                    {system_stats['mem_used']}MB / {system_stats['mem_total']}MB
                </div>
            </div>
            
            <div class="stat-card">
                <h3>💾 磁盘使用</h3>
                <p style="color: {disk_color};">{system_stats['disk_percent']}%</p>
                <div class="progress-bar">
                    <div class="progress-fill disk-progress" style="width: {system_stats['disk_percent']}%;"></div>
                </div>
                <div style="font-size: 0.9em; color: #718096;">
                    {system_stats['disk_used']}GB / {system_stats['disk_total']}GB
                </div>
            </div>
            
            <div class="stat-card">
                <h3>📊 网络流量</h3>
                <div class="network-stats">
                    <div class="network-item">
                        <div class="network-label">⬆️ 发送</div>
                        <div class="network-value">{system_stats['bytes_sent']}MB</div>
                    </div>
                    <div class="network-item">
                        <div class="network-label">⬇️ 接收</div>
                        <div class="network-value">{system_stats['bytes_recv']}MB</div>
                    </div>
                </div>
            </div>
            
            <div class="stat-card">
                <h3>📈 总进程数</h3>
                <p>{len(processes)}</p>
            </div>
            
            <div class="stat-card">
                <h3>⏰ 最后更新</h3>
                <p style="font-size: 1.2em;">{time.strftime('%H:%M:%S')}</p>
            </div>
        </div>
        
        <table>
            <thead>
                <tr>
                    <th>PID</th>
                    <th>用户</th>
                    <th>CPU%</th>
                    <th>内存%</th>
                    <th>命令行</th>
                    <th>操作</th>
                </tr>
            </thead>
            <tbody>
                {processes_html}
            </tbody>
        </table>
        
        <div class="refresh">
            <div style="font-size: 16px; font-weight: bold; color: #007bff; margin-bottom: 5px;">
                ⏰ 倒计时: <span id="timer">30</span>秒
            </div>
            <p>🔄 页面每30秒自动刷新 | ⚠️ 谨慎操作停止进程</p>
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

def run_enhanced_server():
    server = HTTPServer(('0.0.0.0', 8082), EnhancedGUIHandler)
    print("🎨 增强版系统监控启动在 http://localhost:8082")
    print("📊 功能：CPU/内存/磁盘/网络监控 + 进程管理")
    server.serve_forever()

if __name__ == "__main__":
    run_enhanced_server()