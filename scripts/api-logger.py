#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
API 请求日志监听器
==================
纯被动监听，不修改任何系统配置。
Gateway 请求发送到本地 8999 端口 → 监听器记录 → 转发到真实 API。

用法:
  python3 api-logger.py                          # 启动监听
  python3 api-logger.py --status                   # 查看日志统计
  python3 api-logger.py --tail 5                   # 查看最近 N 条
  python3 api-logger.py --clear                    # 清空日志
"""

import json
import os
import sys
import time
import threading
import socket
from http.server import HTTPServer, BaseHTTPRequestHandler
from datetime import datetime, timezone, timedelta
from pathlib import Path
import argparse
import signal
import urllib.request
import urllib.error

# ===== 配置 =====
LOG_DIR = os.path.join(str(Path.home()), ".openclaw", "logs")
LOG_FILE = os.path.join(LOG_DIR, "api-calls.jsonl")
LISTEN_PORT = 8999

# 目标 API
TARGETS = {
    "58.23.129.98:8000": True,
    "58.23.129.98:8001": True,
}

running = True


def get_local_time():
    return datetime.now(timezone(timedelta(hours=8)))


def truncate(text, max_len=1000):
    if text and len(text) > max_len:
        return text[:max_len] + f"\n  ...[截断至{max_len}字符]"
    return text or ""


def get_log_id():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last = json.loads(lines[-1].strip())
                    return last.get("id", 0) + 1
        except:
            pass
    return 1


def save_log(entry):
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def forward_request(target_url, body_bytes):
    """转发请求到真实 API，返回 (status_code, response_body)"""
    try:
        req = urllib.request.Request(
            target_url,
            data=body_bytes,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=120) as resp:
            return resp.status, resp.read()
    except urllib.error.HTTPError as e:
        return e.code, e.read()
    except Exception as e:
        return 500, json.dumps({"error": str(e)}).encode()


class LogHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        start = get_local_time()

        # 读请求体
        length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(length)

        # 解析请求 JSON
        try:
            req_json = json.loads(body)
        except:
            req_json = {}

        # 确定目标
        target_url = "http://58.23.129.98:8000/v1/chat/completions"
        for url in ["8000", "8001"]:
            if f":{url}/v1" in str(self.path) or url in self.path:
                target_url = f"http://58.23.129.98:{url}/v1/chat/completions"
                break

        # 转发请求
        status, resp_body = forward_request(target_url, body)

        # 解析响应
        end = get_local_time()
        duration_ms = int((end - start).total_seconds() * 1000)

        try:
            resp_json = json.loads(resp_body)
        except:
            resp_json = {}

        # 构建日志
        log_id = get_log_id()
        now = get_local_time()
        usage = resp_json.get("usage", {})
        choices = resp_json.get("choices", [])

        entry = {
            "id": log_id,
            "time": now.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "+08:00",
            "target": f"58.23.129.98:{target_url.split(':')[2].split('/')[0]}",
            "duration_ms": duration_ms,
            "request": {
                "model": req_json.get("model", "?"),
                "max_tokens": req_json.get("max_tokens", "?"),
                "temperature": req_json.get("temperature", "?"),
                "messages": req_json.get("messages", []),
                "full": body.decode("utf-8", errors="ignore"),
            },
            "response": {
                "content": choices[0].get("message", {}).get("content", "") if choices else "",
                "reasoning": choices[0].get("message", {}).get("reasoning", "") if choices else "",
                "usage": usage,
                "full": json.dumps(resp_json, ensure_ascii=False),
            },
        }

        save_log(entry)
        print(f"  #{log_id} | {req_json.get('model','?')} | {duration_ms}ms | tokens:{usage.get('total_tokens','?')}")

        # 返回响应
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(resp_body)))
        self.end_headers()
        self.wfile.write(resp_body)

    def log_message(self, *args):
        pass  # 静默


def show_status():
    if not os.path.exists(LOG_FILE):
        print("📭 无日志数据")
        return
    total = tokens = duration = 0
    with open(LOG_FILE, "r") as f:
        for line in f:
            try:
                d = json.loads(line.strip())
                total += 1
                tokens += d.get("response", {}).get("usage", {}).get("total_tokens", 0)
                duration += d.get("duration_ms", 0)
            except:
                pass
    print(f"\n{'='*50}")
    print(f"  📊 API 日志统计")
    print(f"{'='*50}")
    print(f"  总调用:   {total}")
    print(f"  总 Token:  {tokens:,}")
    print(f"  平均 Token: {tokens//total if total else 0:,}")
    print(f"  总耗时:   {duration:,}ms ({duration/1000:.1f}s)")
    print(f"  平均耗时: {duration//total if total else 0}ms")
    print(f"{'='*50}\n")


def show_recent(n=5):
    if not os.path.exists(LOG_FILE):
        print("📭 无日志数据")
        return
    with open(LOG_FILE, "r") as f:
        lines = f.readlines()
    for line in lines[-n:]:
        try:
            d = json.loads(line.strip())
            print(f"📝 #{d['id']} | {d['time']}")
            print(f"  模型: {d['request']['model']}")
            print(f"  耗时: {d['duration_ms']}ms | Token: {d['response']['usage'].get('total_tokens','?')}")
            content = truncate(d['response'].get('content', ''), 200)
            print(f"  回答: {content}")
            print()
        except:
            pass


def main():
    parser = argparse.ArgumentParser(description="API 请求日志监听器")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--tail", type=int, default=0)
    parser.add_argument("--clear", action="store_true")
    args = parser.parse_args()

    if args.status:
        show_status()
        return
    if args.tail:
        show_recent(args.tail)
        return
    if args.clear:
        if os.path.exists(LOG_FILE):
            os.remove(LOG_FILE)
            print("🗑️ 日志已清空")
        return

    os.makedirs(LOG_DIR, exist_ok=True)

    # 检查端口占用
    try:
        s = socket.socket()
        s.connect(("127.0.0.1", LISTEN_PORT))
        s.close()
        print(f"⚠️  监听器已在运行 (:{LISTEN_PORT})")
        return
    except:
        pass

    print("🔍 API 请求日志监听器")
    print("=" * 50)
    print(f"📁 日志: {LOG_FILE}")
    print(f"📡 监听端口: {LISTEN_PORT}")
    print(f"🔄 转发目标: 58.23.129.98:8000 / 8001")
    print()
    print("⚙️ 使用方法:")
    print("  1. 设置环境变量: export OPENCLAW_API_BASE=http://127.0.0.1:{LISTEN_PORT}/v1")
    print("  2. 然后正常运行 OpenClaw")
    print("  3. 所有 API 调用自动记录")
    print("  4. 查看: python3 api-logger.py --status")
    print("  5. 查看最近: python3 api-logger.py --tail 5")
    print("  6. Ctrl+C 停止")
    print("=" * 50)

    server = HTTPServer(("127.0.0.1", LISTEN_PORT), LogHandler)

    def stop(sig, frame):
        print("\n\n🛑 已停止")
        server.shutdown()
        sys.exit(0)

    signal.signal(signal.SIGINT, stop)
    signal.signal(signal.SIGTERM, stop)

    server.serve_forever()


if __name__ == "__main__":
    main()
