#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Token Usage Logger - 轻量级拦截器
=================================
拦截 qwen3.6-35b API 调用，自动记录每次对话的 token 使用量。

用法:
  # 启动
  python3 token_logger.py
  
  # 查看统计
  python3 token_logger.py --stats
  
  # 清理过期日志
  python3 token_logger.py --cleanup
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
import logging
from pathlib import Path
from typing import Dict, Any
from collections import deque

# ===== 配置 =====
REMOTE_URL = os.getenv("QWEN36_REMOTE_URL", "http://58.23.129.98:8000/v1/chat/completions")
PROXY_PORT = int(os.getenv("QWEN36_PROXY_PORT", "18790"))
LOG_DIR = os.path.join(str(Path.home()), ".openclaw", "workspace", "ai_agent", "results")
LOG_FILE = os.path.join(LOG_DIR, "token_usage.log")
STATS_FILE = os.path.join(LOG_DIR, "token_usage_stats.json")
MAX_LOG_DAYS = int(os.getenv("QWEN36_LOG_RETAIN_DAYS", "30"))

# 价格 (元/千token)
PRICE_PROMPT = float(os.getenv("QWEN36_PRICE_PROMPT", "0.04"))
PRICE_COMPLETION = float(os.getenv("QWEN36_PRICE_COMPLETION", "0.10"))

# ===== 全局统计 =====
_lock = threading.RLock()
_stats: Dict[str, Any] = {
    "start_time": datetime.datetime.now().isoformat(),
    "total_requests": 0,
    "total_prompt_tokens": 0,
    "total_completion_tokens": 0,
    "total_tokens": 0,
    "total_cost_cny": 0.0,
    "requests": deque(maxlen=100),
    "by_minute": {},
}

# 日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
logger = logging.getLogger("token_logger")


def _ensure_log_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def _load_stats():
    global _stats
    try:
        _ensure_log_dir()
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE, "r") as f:
                saved = json.load(f)
                _stats.update(saved)
                _stats["requests"] = deque(saved.get("requests", [])[-100:], maxlen=100)
    except Exception as e:
        logger.warning(f"加载历史统计失败: {e}")


def _save_stats():
    try:
        _ensure_log_dir()
        with open(STATS_FILE, "w") as f:
            json.dump(_stats, f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.warning(f"保存统计失败: {e}")


def _append_log(entry: Dict):
    _ensure_log_dir()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _update_usage(prompt_tokens: int, completion_tokens: int, extra: Dict = None) -> Dict:
    with _lock:
        total = prompt_tokens + completion_tokens
        cost = (prompt_tokens / 1000) * PRICE_PROMPT + (completion_tokens / 1000) * PRICE_COMPLETION
        now = datetime.datetime.now()
        minute_key = now.strftime("%Y-%m-%d %H:%M")

        _stats["total_requests"] += 1
        _stats["total_prompt_tokens"] += prompt_tokens
        _stats["total_completion_tokens"] += completion_tokens
        _stats["total_tokens"] += total
        _stats["total_cost_cny"] = round(_stats["total_cost_cny"] + cost, 6)

        if minute_key not in _stats["by_minute"]:
            _stats["by_minute"][minute_key] = {"requests": 0, "prompt": 0, "completion": 0, "tokens": 0, "cost": 0.0}
        m = _stats["by_minute"][minute_key]
        m["requests"] += 1
        m["prompt"] += prompt_tokens
        m["completion"] += completion_tokens
        m["tokens"] += total
        m["cost"] = round(m["cost"] + cost, 6)

        req_entry = {
            "time": now.isoformat(),
            "minute": minute_key,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total,
            "cost_cny": round(cost, 6),
        }
        if extra:
            req_entry.update(extra)
        _stats["requests"].append(req_entry)
        _append_log(req_entry)

        if _stats["total_requests"] % 10 == 0:
            _save_stats()

        return req_entry


class ProxyHandler(http.server.BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        try:
            req_data = json.loads(body)
            msg_count = len(req_data.get("messages", []))
        except:
            msg_count = "?"

        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {os.getenv('QWEN36_KEY', 'sk-78sadn09bjawde123e')}",
            }
            resp = requests.post(REMOTE_URL, data=body, headers=headers, timeout=180)
            response_data = resp.json()

            usage = response_data.get("usage", {})
            pt = usage.get("prompt_tokens", 0)
            ct = usage.get("completion_tokens", 0)
            tt = usage.get("total_tokens", pt + ct)

            if pt or ct:
                req_entry = _update_usage(pt, ct, extra={"messages": msg_count})
                logger.info(
                    f"📝 #{_stats['total_requests']} "
                    f"p:{pt:,} c:{ct:,} t:{tt:,} ¥{req_entry['cost_cny']:.4f}"
                )

            self.send_response(resp.status_code)
            self.end_headers()
            self.wfile.write(resp.content)

        except Exception as e:
            logger.error(f"❌ 转发失败: {e}")
            self.send_response(502)
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e)}).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):
        pass


def _print_stats():
    with _lock:
        s = _stats
        print("\n" + "=" * 64)
        print("  📊 Token Usage 统计")
        print("=" * 64)
        print(f"  总请求:     {s['total_requests']}")
        print(f"  总输入 token:   {s['total_prompt_tokens']:>12,}")
        print(f"  总输出 token:   {s['total_completion_tokens']:>12,}")
        print(f"  总 token:       {s['total_tokens']:>12,}")
        print(f"  估算费用:       ¥{s['total_cost_cny']:>12.4f}")
        print(f"  统计起始:       {s.get('start_time', '未知')}")
        print("=" * 64)

        if s["requests"]:
            recent = list(s["requests"])[-10:]
            print(f"\n  📋 最近 10 次:")
            print(f"  {'时间':<22} {'prompt':>8} {'completion':>10} {'total':>8} {'费用':>10}")
            print(f"  {'-'*66}")
            for r in recent:
                t = r["time"][:19].replace("T", " ")
                print(f"  {t:<22} {r['prompt_tokens']:>8,} {r['completion_tokens']:>10,} {r['total_tokens']:>8,} ¥{r['cost_cny']:>9.4f}")

        if s["by_minute"]:
            minutes = sorted(s["by_minute"].keys())[-10:]
            if minutes:
                print(f"\n  🕐 最近 10 分钟:")
                print(f"  {'时间':<22} {'请求':>6} {'tokens':>10} {'费用':>10}")
                print(f"  {'-'*54}")
                for m in minutes:
                    d = s["by_minute"][m]
                    bar = "█" * min(d["requests"], 30)
                    print(f"  {m:<22} {d['requests']:>6} {d['tokens']:>10,} ¥{d['cost']:>9.4f} {bar}")

        print("\n" + "=" * 64)


def _cleanup_old():
    try:
        if not os.path.exists(LOG_FILE):
            print("📭 日志文件不存在")
            return
        cutoff = time.time() - (MAX_LOG_DAYS * 86400)
        kept = 0
        removed = 0
        with open(LOG_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()
        with open(LOG_FILE + ".tmp", "w", encoding="utf-8") as f:
            for line in lines:
                try:
                    entry = json.loads(line)
                    if datetime.datetime.fromisoformat(entry["time"]).timestamp() > cutoff:
                        f.write(line)
                        kept += 1
                    else:
                        removed += 1
                except:
                    f.write(line)
                    kept += 1
        os.replace(LOG_FILE + ".tmp", LOG_FILE)
        print(f"🧹 清理完成: 保留 {kept} 条, 删除 {removed} 条")
    except Exception as e:
        print(f"❌ 清理失败: {e}")


def main():
    parser = argparse.ArgumentParser(description="Token Usage Logger",
        epilog="""
示例:
  python3 token_logger.py                     # 启动代理
  python3 token_logger.py --stats             # 查看统计
  python3 token_logger.py --cleanup           # 清理过期日志
  python3 token_logger.py --port 18790        # 指定端口
  python3 token_logger.py --remote http://... # 指定远程API
        """)
    parser.add_argument("--stats", action="store_true", help="打印统计")
    parser.add_argument("--cleanup", action="store_true", help="清理过期日志")
    parser.add_argument("--port", type=int, default=PROXY_PORT, help=f"代理端口 (默认 {PROXY_PORT})")
    parser.add_argument("--remote", type=str, default=REMOTE_URL, help="远程 API 地址")
    args = parser.parse_args()

    if args.stats:
        _load_stats()
        _print_stats()
        return

    if args.cleanup:
        _load_stats()
        _cleanup_old()
        return

    _load_stats()
    logger.info(f"🔌 Token Logger 启动")
    logger.info(f"   代理: http://localhost:{args.port}/v1/chat/completions")
    logger.info(f"   转发: {args.remote}")
    logger.info(f"   日志: {LOG_FILE}")

    try:
        with socketserver.TCPServer(("", args.port), ProxyHandler) as httpd:
            logger.info(f"✅ 就绪 (PID: {os.getpid()})")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 48:
            logger.error(f"❌ 端口 {args.port} 已占用: pkill -f token_logger.py")
        else:
            raise


if __name__ == "__main__":
    main()
