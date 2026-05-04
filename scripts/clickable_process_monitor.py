#!/usr/bin/env python3
"""
可点击进程监控驾驶舱 - 支持点击停止进程
"""

import json
import time
import subprocess
import cgi
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

class ClickableProcessMonitor:
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
    
    def get_all_processes(self):
        """获取所有进程数据"""
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
                
                # 风险等级评估
                risk_level = 0
                alerts = []
                
                # 检查未知进程
                is_known = any(known in cmd.lower() for known in self.known_processes)
                if not is_known:
                    risk_level = 1
                    alerts.append("未知进程")
                
                processes.append({
                    'pid': pid,
                    'user': user,
                    'cpu': cpu,
                    'mem': mem,
                    'cmd': cmd[:100] + ('...' if len(cmd) > 100 else ''),
                    'full_cmd': cmd,
                    'risk_level': risk_level,
                    'alerts': alerts
                })
            
            return {
                'total_processes': len(lines),
                'processes': processes,
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            
        except Exception as e:
            return {
                'total_processes': 0,
                'processes': [],
                'last_update': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                'error': str(e)
            }
    
    def kill_process(self, pid):
        """停止进程"""
        try:
            result = subprocess.run(['kill', '-9', pid], capture_output=True, text=True)
            return result.returncode == 0
        except Exception as e:
            return False
    
    def generate_main_page(self, data):
        """生成主页面"""
        processes_html = ""
        for proc in data['processes']:
            row_color = "#ffebee" if proc['risk_level'] >= 2 else "#fff3e0" if proc['risk_level'] >= 1 else ""
            processes_html += f"""
            <tr style="background-color: {row_color};">
                <td>{proc['pid']}</td>
                <td>{proc['user']}</td>
                <td>{proc['cpu']}%</td>
                <td>{proc['mem']}%</td>
                <td>{proc['cmd']}</td>
                <td>{proc['risk_level']}</td>
                <td>{', '.join(proc['alerts'])}</td>
                <td>
                    <form action="/kill" method="post" style="display: inline;">
                        <input type="hidden" name="pid" value="{proc['pid']}">
                        <button type="submit" style="background: #dc3545; color: white; border: none; padding: 5px 10px; border-radius: 3px; cursor: pointer;">
                            ⛔ 停止
                        </button>
                    </form>
                </td>
            </tr>
            """
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>🛡️ 可点击进程监控</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .dashboard {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 20px; }}
        .stat-card {{ background: #f8f9fa; padding: 15极; border-radius: 8px; flex: 1; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        .danger {{ background-color: #ffebee; }}
        .warning {{ background-color: #fff3e0; }}
        button:hover {{ background: #c82333 !important; }}
    </style>
    <meta http-equiv="refresh" content="30">
</head>
<body>
    <div class="dashboard">
        <h1>🛡️ 可点击进程监控</h1>
        
        <div class="stats">
            <div class="stat-card">
                <h3>📊 总进程数</h3>
                <p style="font-size: 24px; margin: 0;">{data['total_processes']}</p>
            </div>
            <div class="stat-card">
                <h3>🕐 最后更新</h3>
                <p style="font-size: 14px; margin: 0;">{data['last_update']}</p>
            </div>
        </div>
        
        <h2>🔍 进程列表 (可点击停止)</h2>
        <table>
            <tr>
                <th>PID</th>
                <th>用户</th>
                <th>CPU%</th>
                <th>内存%</th>
                <th>命令行</th>
                <th>风险等级</th>
                <th>警报信息</th>
                <th>操作</th>
            </tr>
            {processes_html}
        </table>
        
        <div style="margin-top: 20px; color: #666; font-size: 12px;">
            ⚠️ 谨慎操作：停止进程可能导致服务中断
        </div>
    </div>
</body>
</html>
"""

class ClickableDashboardHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        self.monitor = ClickableProcessMonitor()
        super().__init__(*args, **kwargs)
    
    def do_GET(self):
        if self.path == '/':
            data = self.monitor.get_all_processes()
            html = self.monitor.generate_main_page(data)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()
    
    def do_POST(self):
        if self.path == '/kill':
            # 解析表单数据
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length).decode('utf-8')
            fields = cgi.parse_qs(post_data)
            
            pid = fields.get('pid', [''])[0]
            
            if pid and pid.isdigit():
                success = self.monitor.kill_process(pid)
                
                self.send_response(303)  # 重定向
                self.send_header('Location', '/')
                self.end_headers()
            else:
                self.send_response(400)
                self.end_headers()

def run_server():
    server = HTTPServer(('0.0.0.0', 8081), ClickableDashboardHandler)
    print("🚀 可点击进程监控启动在 http://localhost:8081")
    print("🎯 功能：可以点击⛔按钮停止任意进程")
    server.serve_forever()

if __name__ == "__main__":
    run_server()