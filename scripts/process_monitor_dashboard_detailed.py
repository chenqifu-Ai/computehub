#!/usr/bin/env python3
"""
详细版进程监控驾驶舱 - 显示具体监控规则
"""

import json
import time
import subprocess
from datetime import datetime
from http.server import HTTPServer, BaseHTTPRequestHandler

class DetailedProcessMonitorDashboard:
    def __init__(self, port=8081):  # 改用8081端口避免冲突
        self.port = port
        self.known_processes = self._load_known_processes()
        self.suspicious_patterns = self._load_suspicious_patterns()
    
    def _load_known_processes(self):
        return [
            "systemd", "init", "kthreadd", "ksoftirqd", "rcu_sched",
            "sshd", "bash", "python", "node", "java", "nginx", "apache",
            "mysql", "redis", "docker", "containerd", "openclaw",
            "adb", "curl", "wget", "ssh", "scp", "top", "htop", "ps",
            "grep", "awk", "sed", "find", "cat", "ls", "proot"
        ]
    
    def _load_suspicious_patterns(self):
        return [
            "miner", "backdoor", "reverse_shell", "keylogger",
            "crypto", "ransom", "botnet", "trojan", "worm",
            "rootkit", "spyware", "adware", "malware",
            "hidden", "stealth", "obfuscated", "packed"
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
                
                process_name = cmd.split()[0] if cmd else ""
                
                # 分析进程风险
                risk_level, alerts, matched_patterns = self.analyze_process(process_name, cmd, user)
                
                if risk_level > 0:
                    suspicious_count += 1
                
                processes.append({
                    'pid': pid,
                    'user': user,
                    'cpu': cpu,
                    'mem': mem,
                    'cmd': cmd[:100],
                    'risk_level': risk_level,
                    'alerts': alerts,
                    'matched_patterns': matched_patterns,
                    'timestamp': datetime.now().isoformat()
                })
            
            return {
                'total_processes': len(processes),
                'suspicious_count': suspicious_count,
                'processes': processes,
                'last_update': datetime.now().isoformat(),
                'status': 'NORMAL' if suspicious_count == 0 else 'WARNING',
                'known_processes_count': len(self.known_processes),
                'suspicious_patterns_count': len(self.suspicious_patterns),
                'known_processes': self.known_processes,
                'suspicious_patterns': self.suspicious_patterns
            }
            
        except Exception as e:
            return {'error': str(e)}
    
    def analyze_process(self, process_name, cmd, user):
        """分析进程风险"""
        risk_level = 0
        alerts = []
        matched_patterns = []
        
        # 检查已知进程
        is_known = any(known in process_name or known in cmd for known in self.known_processes)
        
        # 检查可疑模式
        for pattern in self.suspicious_patterns:
            if pattern in process_name or pattern in cmd:
                risk_level += 2
                alerts.append(f"包含'{pattern}'")
                matched_patterns.append(pattern)
        
        # 检查异常用户
        normal_users = ['root', 'u0_a355', 'u0_a207', 'u0_a46']
        if user not in normal_users and not user.startswith('u0_a'):
            risk_level += 1
            alerts.append(f"异常用户:{user}")
        
        # 未知进程
        if not is_known and process_name:
            risk_level += 1
            alerts.append("未知进程")
        
        return risk_level, alerts, matched_patterns
    
    def generate_html(self, data):
        """生成详细HTML页面"""
        if 'error' in data:
            return f"""
            <html><body><h1>❌ 错误: {data['error']}</h1></body></html>
            """
        
        status_color = "green" if data['status'] == 'NORMAL' else "red"
        status_emoji = "✅" if data['status'] == 'NORMAL' else "🔴"
        
        # 生成监控规则HTML
        rules_html = ""
        for i, pattern in enumerate(data['suspicious_patterns'], 1):
            rules_html += f"<tr><td>{i}</td><td>{pattern}</td><td>🔴 高风险</td></tr>"
        
        processes_html = ""
        for proc in data['processes']:
            if proc['risk_level'] > 0:
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
                    <td>{', '.join(proc['matched_patterns'])}</td>
                </tr>
                """
        
        return f"""
<!DOCTYPE html>
<html>
<head>
    <title>🛡️ 详细进程监控驾驶舱</title>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
        .dashboard {{ background: white; padding: 20px; border-radius: 10px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
        .status {{ font-size: 24px; font-weight: bold; color: {status_color}; margin-bottom: 20px; }}
        .stats {{ display: flex; gap: 20px; margin-bottom: 20px; flex-wrap: wrap; }}
        .stat-card {{ background: #f8f9fa; padding: 15px; border-radius: 8px; flex: 1; min-width: 200px; }}
        table {{ width: 100%; border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ padding: 12px; text-align: left; border-bottom: 1px solid #ddd; }}
        th {{ background-color: #f2f2f2; }}
        .danger {{ background-color: #ffebee; }}
        .warning {{ background-color: #fff3e0; }}
        .rules-section {{ background: #e8f5e8; padding: 15px; border-radius: 8px; margin-bottom: 20px; }}
    </style>
    <meta http-equiv="refresh" content="10">  <!-- 改为10秒刷新 -->
</head>
<body>
    <div class="dashboard">
        <h1>🛡️ 详细进程监控驾驶舱</h1>
        
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
                <h3>🛡️ 监控规则</h3>
                <p style="font-size: 24px; margin: 0;">{data['suspicious_patterns_count']} 个模式</p>
            </div>
            <div class="stat-card">
                <h3>✅ 已知进程</h3>
                <p style="font-size: 24px; margin: 0;">{data['known_processes_count']} 个</p>
            </div>
        </div>
        
        <div class="rules-section">
            <h2>🔍 监控规则详情 (共{data['suspicious_patterns_count']}个模式)</h2>
            <table>
                <tr><th>#</th><th>可疑模式</th><th>风险等级</th></tr>
                {rules_html}
            </table>
        </div>
        
        <h2>📋 可疑进程列表</h2>
        <table>
            <tr>
                <th>PID</th>
                <th>用户</th>
                <th>CPU%</th>
                <th>内存%</th>
                <th>命令行</th>
                <th>风险等级</th>
                <th>警报信息</th>
                <th>匹配模式</th>
            </tr>
            {processes_html}
        </table>
        
        <div style="margin-top: 20px; color: #666; font-size: 12px;">
            🕐 最后更新: {data['last_update']} | 🔄 每10秒自动刷新 | 🛡️ 监控系统版本 2.0
        </div>
    </div>
</body>
</html>
"""

class DetailedDashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            monitor = DetailedProcessMonitorDashboard()
            data = monitor.get_process_data()
            html = monitor.generate_html(data)
            
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(html.encode('utf-8'))
        else:
            self.send_response(404)
            self.end_headers()

def start_detailed_dashboard(port=8081):
    """启动详细监控驾驶舱"""
    server = HTTPServer(('0.0.0.0', port), DetailedDashboardHandler)
    print(f"🚀 详细进程监控驾驶舱已启动: http://localhost:{port}")
    print(f"📊 监控频率: 每10秒自动刷新")
    print(f"🔍 显示: 17个具体可疑模式")
    print("⏹️  按 Ctrl+C 停止服务")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n🛑 监控驾驶舱已停止")
        server.shutdown()

if __name__ == "__main__":
    start_detailed_dashboard()