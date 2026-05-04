#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token Usage Logger - API 代理拦截器
==================================
拦截所有对 qwen3.6-35b 的 API 请求，记录 token 使用量。

用法:
  # 启动代理 (默认 18790 端口)
  python3 token_logger.py
  
  # 然后把模型 API 地址改为 http://localhost:18790/v1/chat/completions
  
  # 查看日志
  python3 token_logger.py --stats
"""

import http.server
import socketserver
import json
import os
import sys
import time
import datetime
import argparse
import requests
import threading
from pathlib import Path
from urllib.parse import urlparse, parse_qs
from typing import Dict, Any, Optional

# ===== 配置 =====
REMOTE_URL = os.getenv("QWEN36_REMOTE_URL", "http://58.23.129.98:8000/v1/chat/completions")
PROXY_PORT = int(os.getenv("QWEN36_PROXY_PORT", "18790"))
LOG_DIR = os.getenv("QWEN36_LOG_DIR", str(Path.home() / ".openclaw/workspace/ai_agent/results"))
LOG_FILE = os.path.join(LOG_DIR, "token_usage.log")
STATS_FILE = os.path.join(LOG_DIR, "token_usage_stats.json")
MAX_LOG_DAYS = int(os.getenv("QWEN36_LOG_RETAIN_DAYS", "30"))

# ===== Token 统计 =====
_lock = threading.Lock()
_stats: Dict[str, Any] = {
    "start_time": datetime.datetime.now().isoformat(),
    "total_requests": 0,
    "total_prompt_tokens": 0,
    "total_completion_tokens": 0,
    "total_tokens": 0,
    "total_cost_cny": 0.0,
    "requests": [],  # 最近 100 条
}

# 价格模型（百炼 qwen3.6-35b 的定价，实际以API返回为准）
PRICE_PER_1K_PROMPT = 0.04   # 每千 token ¥0.04
PRICE_PER_1K_COMPLETION = 0.10  # 每千 token ¥0.10


def _load_stats() -> Dict:
    """加载之前的统计数据"""
    global _stats
    try:
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r") as f:
                saved = json.load(f)
                _stats.update(saved)
                # 保留 requests 列表（最多 100 条）
                saved_requests = saved.get("requests", [])
                _stats["requests"] = saved_requests[-100:]
    except:
        pass
    return _stats


def _save_stats():
    """保存统计数据到文件"""
    try:
        os.makedirs(LOG_DIR, exist_ok=True)
        with open(STATS_FILE, "w") as f:
            json.dump(_stats, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"❌ 保存统计失败: {e}", file=sys.stderr)


def _append_log(entry: Dict):
    """追加到日志文件"""
    os.makedirs(LOG_DIR, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _update_usage(prompt_tokens: int, completion_tokens: int):
    """更新全局统计数据"""
    global _stats
    with _lock:
        total = prompt_tokens + completion_tokens
        _stats["total_requests"] += 1
        _stats["total_prompt_tokens"] += prompt_tokens
        _stats["total_completion_tokens"] += completion_tokens
        _stats["total_tokens"] += total
        # 估算费用 (元)
        cost = (prompt_tokens / 1000) * PRICE_PER_1K_PROMPT + \
               (completion_tokens / 1000) * PRICE_PER_1K_COMPLETION
        _stats["total_cost_cny"] = round(_stats["total_cost_cny"] + cost, 6)

        # 记录最近请求
        entry = {
            "time": datetime.datetime.now().isoformat(),
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total,
            "cost_cny": round(cost, 6),
        }
        _stats["requests"].append(entry)
        _stats["requests"] = _stats["requests"][-100:]  # 保留最近 100 条

        # 定期保存
        if _stats["total_requests"] % 5 == 0:
            _save_stats()
            _append_log(entry)


def _print_stats():
    """打印统计摘要"""
    with _lock:
        s = _stats
        print("\n" + "=" * 60)
        print("📊 Token 使用统计")
        print("=" * 60)
        print(f"  总请求次数:     {s['total_requests']}")
        print(f"  总输入 token:   {s['total_prompt_tokens']:,}")
        print(f"  总输出 token:   {s['total_completion_tokens']:,}")
        print(f"  总 token 数:    {s['total_tokens']:,}")
        print(f"  估算费用:       ¥{s['total_cost_cny']:.4f}")
        print(f"  统计起始时间:   {s.get('start_time', '未知')}")
        print("=" * 60)
        
        # 最近 5 条
        if s["requests"]:
            print(f"\n  最近 5 次请求:")
            for r in s["requests"][-5:]:
                print(f"    {r['time']}  |  prompt:{r['prompt_tokens']:,}  completion:{r['completion_tokens']:,}  费用:¥{r['cost_cny']:.4f}")
        print()


def _cleanup_old_logs():
    """清理超过保留期的日志"""
    try:
        if os.path.exists(LOG_FILE):
            cutoff = time.time() - (MAX_LOG_DAYS * 86400)
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            new_lines = []
            for line in lines:
                try:
                    entry = json.loads(line)
                    entry_time = datetime.datetime.fromisoformat(entry["time"])
                    if entry_time.timestamp() > cutoff:
                        new_lines.append(line)
                except:
                    new_lines.append(line)  # 保留无法解析的
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.writelines(new_lines)
            print(f"🧹 日志清理完成 (保留{MAX_LOG_DAYS}天)")
    except Exception as e:
        print(f"⚠️ 日志清理失败: {e}", file=sys.stderr)


class TokenLoggingHandler(http.server.BaseHTTPRequestHandler):
    """HTTP 代理处理器 - 记录 token 使用量"""
    
    def do_POST(self):
        # 读取请求体
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""
        
        # 转发请求到远程 API
        try:
            resp = requests.post(
                REMOTE_URL,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.getenv('QWEN36_KEY', 'sk-78sadn09bjawde123e')}",
                },
                timeout=120,
            )
            
            # 解析响应
            response_data = resp.json()
            
            # 提取 usage
            usage = response_data.get("usage", {})
            prompt_tokens = usage.get("prompt_tokens", 0)
            completion_tokens = usage.get("completion_tokens", 0)
            
            # 记录 token 使用
            if prompt_tokens or completion_tokens:
                _update_usage(prompt_tokens, completion_tokens)
                print(f"📝 #{_stats['total_requests']}  prompt:{prompt_tokens:,}  completion:{completion_tokens:,}")
            
            # 发送响应
            self.send_response(resp.status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp.content)
            
        except Exception as e:
            print(f"❌ 转发失败: {e}", file=sys.stderr)
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())
    
    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        pass  # 静默模式，不打印到 stderr


def main():
    parser = argparse.ArgumentParser(description="Token Usage Logger - API 代理拦截器")
    parser.add_argument("--stats", action="store_true", help="打印统计摘要")
    parser.add_argument("--cleanup", action="store_true", help="清理过期日志")
    parser.add_argument("--port", type=int, default=PROXY_PORT, help="代理端口 (默认 18790)")
    parser.add_argument("--remote", type=str, default=REMOTE_URL, help="远程 API 地址")
    args = parser.parse_args()
    
    if args.stats:
        _load_stats()
        _print_stats()
        return
    
    if args.cleanup:
        _load_stats()
        _cleanup_old_logs()
        return
    
    # 加载历史统计
    _load_stats()
    
    REMOTE_URL = args.remote
    
    print(f"🔌 Token Logger 启动")
    print(f"   代理地址: http://localhost:{args.port}/v1/chat/completions")
    print(f"   转发到:   {REMOTE_URL}")
    print(f"   日志文件: {LOG_FILE}")
    print(f"   统计文件: {STATS_FILE}")
    print()
    print("💡 使用方式:")
    print(f"   1. 设置 API URL: export OPENAI_API_BASE=http://localhost:{args.port}/v1")
    print(f"   2. 查看统计: python3 {sys.argv[0]} --stats")
    print(f"   3. 清理日志: python3 {sys.argv[0]} --cleanup")
    print()
    
    # 启动代理服务器
    with socketserver.TCPServer(("", args.port), TokenLoggingHandler) as httpd:
        httpd.serve_forever()


if __name__ == "__main__":
    main()
