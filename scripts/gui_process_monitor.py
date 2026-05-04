#!/usr/bin/env python3
"""
图形界面进程监控 - 带停止按钮
"""

import subprocess
import time
from http.server import HTTPServer, BaseHTTPRequestHandler

class GUIProcessMonitor:
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
    
    def kill_process(self, pid):
        """停止进程"""
        try:
            result = subprocess.run(['kill', '-9', pid], capture_output=True, text=True)
            return result.returncode == 0
        except Exception:
            return False

class GUIHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.monitor = GUIProcessMonitor()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            processes = self.monitor.get_processes()
            html = self._generate_html(processes)
            
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
    
    def _generate_html(self, processes):
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
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>🖥️ 图形进程监控</title>
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
            max-width: 1200px;
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
            display: flex;
            gap: 20px;
            margin-bottom: 30px;
            justify-content: center;
        }}
        .stat-card {{
            background: #f7fafc;
            padding: 20px;
            border-radius: 10px;
            text-align: center;
            flex: 1;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }}
        .stat-card h3 {{
            margin: 0 0 10px 0;
            color: #4a5568;
            font-size: 1.1em;
        }}
        .stat-card p {{
            font-size: 2em;
            margin: 0;
            color: #2d3748;
            font-weight: bold;
        }}
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
    </style>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🖥️ 图形进程监控系统</h1>
            <p>实时监控系统进程，支持一键停止</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <h3>📊 总进程数</h3>
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

def run_server():
    server = HTTPServer(('0.0.0.0', 8081), GUIHandler)
    print("🎨 图形界面进程监控启动在 http://localhost:8081")
    print("🖱️  功能：美观界面 + 点击停止按钮")
    server.serve_forever()

if __name__ == "__main__":
    run_server()