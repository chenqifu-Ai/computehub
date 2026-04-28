#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
OpenClaw Token Interceptor - 网关级 token 拦截器
=================================================
拦截 OpenClaw Gateway 对模型 API 的所有调用，记录 token 使用量。

用法:
  # 1. 启动拦截器
  python3 token_interceptor.py
  
  # 2. 拦截器会输出代理配置信息
  #    将 models.json 中 baseURL 改为: http://localhost:18791/v1
  
  # 3. 查看所有统计
  python3 token_interceptor.py --stats
  
  # 4. 查看今日
  python3 token_interceptor.py --today
  
  # 5. 按天趋势
  python3 token_interceptor.py --trend
  
  # 6. 导出 CSV
  python3 token_interceptor.py --export
  
  # 7. 清理旧日志
  python3 token_interceptor.py --cleanup
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
import hashlib
import threading
import logging
from pathlib import Path
from typing import Dict, Any
from collections import deque
from urllib.parse import urlparse

# ===== 配置 =====
PROXY_PORT = int(os.getenv("INTERCEPTOR_PORT", "18791"))
REMOTE_URLS = {
    "qwen36": os.getenv("QWEN36_REMOTE_URL", "http://58.23.129.98:8000/v1/chat/completions"),
    "gemma": os.getenv("GEMMA_REMOTE_URL", "http://58.23.129.98:8001/v1/chat/completions"),
}
LOG_DIR = os.path.join(str(Path.home()), ".openclaw", "workspace", "ai_agent", "results")
LOG_FILE = os.path.join(LOG_DIR, "token_interceptor.jsonl")
STATS_FILE = os.path.join(LOG_DIR, "token_interceptor_stats.json")
CSV_FILE = os.path.join(LOG_DIR, "token_usage.csv")
MAX_RETAIN_DAYS = int(os.getenv("INTERCEPTOR_RETAIN_DAYS", "30"))

# 定价 (元/千token) - 按实际 API 定价
PRICES = {
    "qwen3.6-35b": {"prompt": 0.04, "completion": 0.10, "model": "qwen3.6-35b"},
    "gemma-4-31b": {"prompt": 0.02, "completion": 0.06, "model": "gemma-4-31b"},
    "default": {"prompt": 0.03, "completion": 0.08},
}

# ===== 全局状态 =====
_lock = threading.RLock()
_stats = {
    "started": datetime.datetime.now().isoformat(),
    "total_requests": 0,
    "total_prompt_tokens": 0,
    "total_completion_tokens": 0,
    "total_tokens": 0,
    "total_cost": 0.0,
    "models": {},
    "requests": deque(maxlen=200),
}

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger("interceptor")


# ===== 数据持久化 =====
def _ensure_dir():
    os.makedirs(LOG_DIR, exist_ok=True)


def _load_stats():
    global _stats
    try:
        _ensure_dir()
        if os.path.exists(STATS_FILE):
            with open(STATS_FILE) as f:
                s = json.load(f)
                _stats.update(s)
                _stats["requests"] = deque(s.get("requests", [])[-200:], maxlen=200)
    except Exception as e:
        log.warning(f"加载历史失败: {e}")


def _save_stats():
    try:
        s = dict(_stats)
        s["requests"] = list(_stats["requests"])
        with open(STATS_FILE, "w") as f:
            json.dump(s, f, ensure_ascii=False, indent=2)
    except:
        pass


def _append_log(entry: dict):
    _ensure_dir()
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


# ===== 核心逻辑 =====
def _detect_model(messages: list) -> str:
    """从 messages 中检测对话场景"""
    if not messages:
        return "unknown"
    last = messages[-1].get("content", "")[:200]
    # 简单分类
    if any(k in last.lower() for k in ["code", "function", "class ", "def ", "import "]):
        return "code"
    if any(k in last.lower() for k in ["计算", "数学", "公式", "等于", "多少"]):
        return "math"
    if any(k in last.lower() for k in ["股票", "股价", "行情", "持仓", "交易"]):
        return "finance"
    if any(k in last.lower() for k in ["分析", "总结", "报告", "数据"]):
        return "analysis"
    return "general"


def _update_usage(model_name: str, prompt_tokens: int, completion_tokens: int,
                  messages_count: int, scenario: str):
    """更新统计数据并持久化"""
    with _lock:
        total = prompt_tokens + completion_tokens
        price_info = PRICES.get(model_name, PRICES["default"])
        cost = (prompt_tokens / 1000) * price_info["prompt"] + \
               (completion_tokens / 1000) * price_info["completion"]

        _stats["total_requests"] += 1
        _stats["total_prompt_tokens"] += prompt_tokens
        _stats["total_completion_tokens"] += completion_tokens
        _stats["total_tokens"] += total
        _stats["total_cost"] = round(_stats["total_cost"] + cost, 6)

        # 按模型分组
        if model_name not in _stats["models"]:
            _stats["models"][model_name] = {
                "requests": 0, "prompt": 0, "completion": 0,
                "tokens": 0, "cost": 0.0
            }
        m = _stats["models"][model_name]
        m["requests"] += 1
        m["prompt"] += prompt_tokens
        m["completion"] += completion_tokens
        m["tokens"] += total
        m["cost"] = round(m["cost"] + cost, 6)

        now = datetime.datetime.now()
        req_entry = {
            "time": now.isoformat(),
            "minute": now.strftime("%Y-%m-%d %H:%M"),
            "model": model_name,
            "prompt_tokens": prompt_tokens,
            "completion_tokens": completion_tokens,
            "total_tokens": total,
            "cost": round(cost, 6),
            "messages": messages_count,
            "scenario": scenario,
        }
        _stats["requests"].append(req_entry)

        # 持久化
        _append_log(req_entry)
        if _stats["total_requests"] % 5 == 0:
            _save_stats()

        return req_entry


class InterceptorHandler(http.server.BaseHTTPRequestHandler):
    """HTTP 拦截代理"""

    def _get_remote(self) -> tuple:
        """根据 URL 确定远程地址和模型名"""
        if "8000" in self.path or "qwen" in str(self.client_address):
            return REMOTE_URLS["qwen36"], "qwen3.6-35b"
        elif "8001" in self.path or "gemma" in str(self.client_address):
            return REMOTE_URLS["gemma"], "gemma-4-31b"
        else:
            # 默认转发到 qwen36
            return REMOTE_URLS["qwen36"], "qwen3.6-35b"

    def do_POST(self):
        # 读取请求
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length) if content_length > 0 else b""

        # 解析请求信息
        try:
            req_data = json.loads(body)
            messages = req_data.get("messages", [])
            msg_count = len(messages)
            max_tokens = req_data.get("max_tokens", req_data.get("n_ctx", 4096))
        except:
            messages = []
            msg_count = 0
            max_tokens = 4096

        scenario = _detect_model(messages) if messages else "unknown"

        # 获取远程地址
        remote_url, model_name = self._get_remote()

        try:
            # 转发请求
            resp = requests.post(
                remote_url,
                data=body,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {os.getenv('API_KEY', 'sk-78sadn09bjawde123e')}",
                },
                timeout=180,
            )

            # 解析响应
            resp_data = resp.json()
            usage = resp_data.get("usage", {})
            pt = usage.get("prompt_tokens", 0)
            ct = usage.get("completion_tokens", 0)
            tt = usage.get("total_tokens", pt + ct)

            # 记录 token 使用
            if pt or ct:
                entry = _update_usage(model_name, pt, ct, msg_count, scenario)
                log.info(
                    f"📝 #{_stats['total_requests']:>5} "
                    f"{model_name:15} "
                    f"p:{pt:>8,} c:{ct:>8,} "
                    f"t:{tt:>8,} "
                    f"¥{entry['cost']:>8.4f} "
                    f"│ {scenario}"
                )

            # 返回响应
            self.send_response(resp.status_code)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(resp.content)

        except Exception as e:
            log.error(f"❌ 转发失败: {e}")
            self.send_response(502)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps({"error": str(e), "remote": remote_url}).encode())

    def log_message(self, format, *args):
        pass  # 抑制默认日志


# ===== 统计命令 =====
def print_stats(all_records: list, title=""):
    if not all_records:
        print("📭 无记录")
        return

    total_pt = sum(r.get("prompt_tokens", 0) for r in all_records)
    total_ct = sum(r.get("completion_tokens", 0) for r in all_records)
    total_t = total_pt + total_ct
    total_cost = sum(r.get("cost", 0) for r in all_records)
    n = len(all_records)

    print("\n" + "=" * 72)
    print(f"  📊 Token 拦截统计 {title}")
    print("=" * 72)
    print(f"  请求次数:   {n:>10}")
    print(f"  输入 token: {total_pt:>10,}")
    print(f"  输出 token: {total_ct:>10,}")
    print(f"  总 token:   {total_t:>10,}")
    print(f"  平均输入:   {total_pt//n:>10,}" if n else "")
    print(f"  平均输出:   {total_ct//n:>10,}" if n else "")
    print(f"  估算费用:   ¥{total_cost:>10.4f}")
    print("=" * 72)


def print_top(records, n=20):
    sorted_r = sorted(records, key=lambda r: r.get("total_tokens", 0), reverse=True)
    print(f"\n  🔝 前 {n} 大请求:")
    print(f"  {'时间':<22} {'模型':<15} {'输入':>8} {'输出':>8} {'总':>8} {'费用':>10} {'场景'}")
    print(f"  {'-'*76}")
    for r in sorted_r[:n]:
        t = r.get("time", "?")[:19].replace("T", " ")
        print(f"  {t:<22} {r.get('model','?'):<15} "
              f"{r.get('prompt_tokens',0):>8,} {r.get('completion_tokens',0):>8,} "
              f"{r.get('total_tokens',0):>8,} ¥{r.get('cost',0):>9.4f} "
              f"{r.get('scenario','?')}")
    print()


def print_trend(records):
    days = {}
    for r in records:
        d = r.get("time", "")[:10]
        if d not in days:
            days[d] = {"requests": 0, "prompt": 0, "completion": 0, "cost": 0.0}
        days[d]["requests"] += 1
        days[d]["prompt"] += r.get("prompt_tokens", 0)
        days[d]["completion"] += r.get("completion_tokens", 0)
        days[d]["cost"] += r.get("cost", 0)

    if not days:
        return
    print(f"\n  📈 按天趋势:")
    print(f"  {'日期':<12} {'请求':>6} {'输入':>10} {'输出':>10} {'费用':>10}")
    print(f"  {'-'*54}")
    for d in sorted(days.keys()):
        v = days[d]
        print(f"  {d:<12} {v['requests']:>6} {v['prompt']:>10,} {v['completion']:>10,} ¥{v['cost']:>9.4f}")
    print()


def print_hourly(records):
    hours = {}
    for r in records:
        h = r.get("time", "")[11:13] + ":00"
        if h not in hours:
            hours[h] = {"requests": 0, "prompt": 0, "completion": 0, "cost": 0.0}
        hours[h]["requests"] += 1
        hours[h]["prompt"] += r.get("prompt_tokens", 0)
        hours[h]["completion"] += r.get("completion_tokens", 0)
        hours[h]["cost"] += r.get("cost", 0)

    if not hours:
        return
    print(f"\n  🕐 按小时分布:")
    print(f"  {'小时':<8} {'请求':>6} {'输入':>10} {'输出':>10} {'费用':>10} {'活跃'}")
    print(f"  {'-'*58}")
    for h in sorted(hours.keys()):
        v = hours[h]
        bar = "🟩" * min(v["requests"], 30)
        print(f"  {h:<8} {v['requests']:>6} {v['prompt']:>10,} {v['completion']:>10,} ¥{v['cost']:>9.4f} {bar}")
    print()


def export_csv(records):
    if not records:
        print("📭 无记录")
        return
    with open(CSV_FILE, "w", encoding="utf-8") as f:
        f.write("time,model,prompt_tokens,completion_tokens,total_tokens,cost,scenario\n")
        for r in records:
            f.write(f"{r.get('time','')},{r.get('model','')},{r.get('prompt_tokens',0)},")
            f.write(f"{r.get('completion_tokens',0)},{r.get('total_tokens',0)},")
            f.write(f"{r.get('cost',0)},{r.get('scenario','')}\n")
    print(f"📁 已导出: {CSV_FILE} ({len(records)} 条)")


def _cleanup():
    try:
        if not os.path.exists(LOG_FILE):
            print("📭 日志不存在")
            return
        cutoff = time.time() - (MAX_RETAIN_DAYS * 86400)
        kept = 0
        removed = 0
        with open(LOG_FILE, "r") as f:
            lines = f.readlines()
        with open(LOG_FILE + ".tmp", "w") as f:
            for line in lines:
                try:
                    e = json.loads(line)
                    if datetime.datetime.fromisoformat(e["time"]).timestamp() > cutoff:
                        f.write(line)
                        kept += 1
                    else:
                        removed += 1
                except:
                    f.write(line)
                    kept += 1
        os.replace(LOG_FILE + ".tmp", LOG_FILE)
        print(f"🧹 保留 {kept} 条, 删除 {removed} 条")
    except Exception as e:
        print(f"❌ 清理失败: {e}")


def _load_all_records() -> list:
    records = []
    if not os.path.exists(LOG_FILE):
        return records
    with open(LOG_FILE, "r", encoding="utf-8") as f:
        for line in f:
            try:
                records.append(json.loads(line))
            except:
                continue
    return records


# ===== 主入口 =====
def main():
    parser = argparse.ArgumentParser(
        description="OpenClaw Token Interceptor",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python3 token_interceptor.py                 # 启动拦截器
  python3 token_interceptor.py --stats         # 全部统计
  python3 token_interceptor.py --today         # 今日
  python3 token_interceptor.py --top 20        # 前 20 大请求
  python3 token_interceptor.py --hourly        # 按小时
  python3 token_interceptor.py --trend         # 按天趋势
  python3 token_interceptor.py --export        # 导出 CSV
  python3 token_interceptor.py --cleanup       # 清理旧日志
        """
    )
    parser.add_argument("--stats", action="store_true", help="全部统计")
    parser.add_argument("--today", action="store_true", help="今日统计")
    parser.add_argument("--top", type=int, default=0, help="前 N 大请求")
    parser.add_argument("--hourly", action="store_true", help="按小时分布")
    parser.add_argument("--trend", action="store_true", help="按天趋势")
    parser.add_argument("--export", action="store_true", help="导出 CSV")
    parser.add_argument("--cleanup", action="store_true", help="清理旧日志")
    parser.add_argument("--port", type=int, default=PROXY_PORT, help=f"代理端口 (默认 {PROXY_PORT})")
    args = parser.parse_args()

    # 加载历史
    _load_stats()

    if args.stats:
        records = _load_all_records() or list(_stats.get("requests", []))
        print_stats(records)
        if _stats.get("models"):
            print("\n  📦 按模型:")
            for m, d in _stats["models"].items():
                print(f"    {m:<15} 请求:{d['requests']:>6} "
                      f"tokens:{d['tokens']:>10,} 费用:¥{d['cost']:.4f}")
        print()
        return

    if args.today:
        today_str = datetime.date.today().isoformat()
        records = [r for r in _load_all_records() if r.get("time", "").startswith(today_str)]
        print_stats(records, "📅 今日")
        return

    if args.top:
        records = _load_all_records()
        print_top(records, args.top)
        return

    if args.hourly:
        records = _load_all_records()
        print_hourly(records)
        return

    if args.trend:
        records = _load_all_records()
        print_trend(records)
        return

    if args.export:
        records = _load_all_records()
        export_csv(records)
        return

    if args.cleanup:
        _cleanup()
        return

    # ===== 启动拦截代理 =====
    log.info(f"🔌 Token Interceptor 启动")
    log.info(f"   代理地址: http://localhost:{args.port}/v1")
    log.info(f"   转发到 qwen36: {REMOTE_URLS['qwen36']}")
    log.info(f"   转发到 gemma:  {REMOTE_URLS['gemma']}")
    log.info(f"   日志文件: {LOG_FILE}")
    log.info(f"   统计文件: {STATS_FILE}")
    log.info(f"")
    log.info(f"   💡 配置 models.json:")
    log.info(f"      baseURL: http://localhost:{args.port}/v1")
    log.info(f"   💡 查看统计: python3 {sys.argv[0]} --stats")

    try:
        with socketserver.TCPServer(("", args.port), InterceptorHandler) as httpd:
            log.info(f"✅ 拦截器就绪 (PID: {os.getpid()})")
            httpd.serve_forever()
    except OSError as e:
        if e.errno == 48:
            log.error(f"❌ 端口 {args.port} 已占用: pkill -f token_interceptor.py")
        else:
            raise


if __name__ == "__main__":
    main()
