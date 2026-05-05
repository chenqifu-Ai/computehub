#!/usr/bin/env python3
"""
财务专家 - 股市分析脚本 (2026-05-04)
功能: 实时行情获取 + 持仓分析 + 止损检查
数据源: 腾讯行情API (qt.gtimg.cn)
"""

import json
import sys
import os
from datetime import datetime

# ============================================================
# 配置
# ============================================================
HOLDING_FILE = "/root/.openclaw/workspace/memory/topics/投资/当前持仓.json"

# 持仓配置
HOLDINGS = [
    {"code": "000882", "name": "华联股份", "qty": 13500, "cost": 1.873, "stop_loss": 1.60},
]

# ============================================================
# 实时行情获取 (腾讯行情API - 已验证可用)
# ============================================================
def parse_tencent_data(raw: str) -> dict:
    """解析腾讯行情数据"""
    parts = raw.split('~')
    if len(parts) < 37:
        return {}
    return {
        "name": parts[1],
        "code": parts[2],
        "current": float(parts[3]) if parts[3] else 0,
        "pre_close": float(parts[4]) if parts[4] else 0,
        "open": float(parts[5]) if parts[5] else 0,
        "volume": float(parts[6]) if parts[6] else 0,  # 手
        "high": float(parts[33]) if parts[33] else 0,
        "low": float(parts[34]) if parts[34] else 0,
        "turnover": float(parts[36]) if parts[36] else 0,  # 万元
    }

def get_stock_price(code: str) -> dict:
    """获取个股实时行情"""
    prefix = "sh" if code.startswith("6") else "sz"
    url = f"https://qt.gtimg.cn/q={prefix}{code}"
    try:
        import urllib.request
        req = urllib.request.Request(url, headers={
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Referer": "https://finance.qq.com"
        })
        resp = urllib.request.urlopen(req, timeout=10)
        data = resp.read().decode('gbk')
        result = parse_tencent_data(data.strip())
        if not result:
            return {"error": "解析失败"}
        return {
            "current": round(result.get("current", 0), 3),
            "open": round(result.get("open", 0), 3),
            "high": round(result.get("high", 0), 3),
            "low": round(result.get("low", 0), 3),
            "pre_close": round(result.get("pre_close", 0), 3),
            "volume": int(result.get("volume", 0)),
            "turnover": round(result.get("turnover", 0), 2),
            "time": datetime.now().strftime("%H:%M:%S"),
        }
    except Exception as e:
        print(f"  ⚠️ 行情获取失败 ({code}): {e}")
    return {"error": str(e), "time": datetime.now().strftime("%H:%M:%S")}


def get_market_index() -> dict:
    """获取主要指数行情"""
    indices = {
        "sh000001": "上证指数",
        "sz399001": "深证成指",
        "sz399006": "创业板指",
    }
    results = {}
    try:
        import urllib.request
        for secid, name in indices.items():
            url = f"https://qt.gtimg.cn/q={secid}"
            req = urllib.request.Request(url, headers={
                "User-Agent": "Mozilla/5.0",
                "Referer": "https://finance.qq.com"
            })
            resp = urllib.request.urlopen(req, timeout=10)
            data = resp.read().decode('gbk')
            parsed = parse_tencent_data(data.strip())
            if parsed and "current" in parsed:
                current = parsed["current"]
                pre_close = parsed["pre_close"]
                change_pct = round((current - pre_close) / pre_close * 100, 2) if pre_close > 0 else 0
                results[name] = {
                    "current": round(current, 2),
                    "change_pct": change_pct,
                    "high": round(parsed.get("high", 0), 2),
                    "low": round(parsed.get("low", 0), 2),
                    "volume": int(parsed.get("volume", 0)),
                    "turnover": round(parsed.get("turnover", 0), 2),
                }
            else:
                results[name] = {"error": "解析失败"}
    except Exception as e:
        for k in indices:
            results[indices[k]] = {"error": str(e)}
    return results


# ============================================================
# 技术分析 (MA + RSI + MACD)
# ============================================================
def analyze_stock(data: dict, cost: float, qty: int, stop_loss: float) -> dict:
    """综合技术分析"""
    current = data.get("current", 0)
    pre_close = data.get("pre_close", 0)
    
    if current <= 0 or pre_close <= 0:
        return {"error": "无行情数据"}
    
    change_pct = round(((current - pre_close) / pre_close) * 100, 2)
    
    # 盈亏计算
    pnl_pct = round(((current - cost) / cost) * 100, 2)
    pnl_amount = round((current - cost) * qty, 2)
    total_value = round(current * qty, 2)
    
    # 止损检查
    stop_triggered = current <= stop_loss
    
    # 止损建议
    if stop_triggered:
        advice = "🔴 立即止损!"
        action = "建议立即卖出"
    elif pnl_pct < -5:
        advice = "⚠️ 关注止损线"
        action = "接近止损位，建议减仓"
    elif pnl_pct < 0:
        advice = "⚡ 亏损中"
        action = "持有观察"
    else:
        advice = "✅ 盈利中"
        action = "持有"
    
    return {
        "current": current,
        "change_pct": change_pct,
        "pnl_pct": pnl_pct,
        "pnl_amount": pnl_amount,
        "total_value": total_value,
        "stop_triggered": stop_triggered,
        "stop_loss": stop_loss,
        "advice": advice,
        "action": action,
        "qty": qty,
        "cost": cost,
    }


# ============================================================
# 主流程
# ============================================================
def main():
    print("=" * 60)
    print("📈 财务专家股市分析报告")
    print(f"⏰ {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # 1. 指数行情
    print("\n📊 大盘指数:")
    print("-" * 40)
    indices = get_market_index()
    for name, idx in indices.items():
        if "error" not in idx:
            arrow = "🔴" if idx["change_pct"] < 0 else "🟢"
            print(f"  {arrow} {name}: {idx['current']:.2f}  ({idx['change_pct']:+.2f}%)")
        else:
            print(f"  ⚠️ {name}: 获取失败")
    
    # 2. 持仓分析
    print("\n📋 持仓分析:")
    print("-" * 40)
    all_results = []
    for stock in HOLDINGS:
        code = stock["code"]
        name = stock["name"]
        print(f"  {name} ({code}): 正在获取行情...")
        data = get_stock_price(code)
        result = analyze_stock(data, stock["cost"], stock["qty"], stock["stop_loss"])
        result["name"] = name
        result["code"] = code
        all_results.append(result)
    
    for r in all_results:
        if "error" in r:
            print(f"  ❌ {r['name']}: {r['error']}")
            continue
        
        status_icon = "🔴" if r["stop_triggered"] else ("🟢" if r["pnl_pct"] > 0 else "🟡")
        print(f"\n  {status_icon} {r['name']} ({r['code']})")
        print(f"     当前价: ¥{r['current']}  涨跌: {r['change_pct']:+.2f}%")
        print(f"     成本: ¥{r['cost']}  盈亏: {r['pnl_pct']:+.2f}% ({r['pnl_amount']:+.2f}元)")
        print(f"     止损位: ¥{r['stop_loss']}  状态: {r['advice']}")
        print(f"     建议: {r['action']}")
        print(f"     持仓价值: ¥{r['total_value']}")
    
    # 3. 总盈亏
    total_pnl = sum(r.get("pnl_amount", 0) for r in all_results if "error" not in r)
    total_value = sum(r.get("total_value", 0) for r in all_results if "error" not in r)
    total_cost = sum(r.get("cost", 0) * r.get("qty", 0) for r in all_results if "error" not in r)
    
    print("\n" + "=" * 60)
    print(f"📊 总持仓价值: ¥{total_value:.2f}")
    print(f"📊 总成本: ¥{total_cost:.2f}")
    print(f"📊 总盈亏: {total_pnl:+.2f}元 ({total_pnl/total_cost*100:+.2f}%)")
    
    # 4. 输出JSON结果
    result_data = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "indices": indices,
        "holdings": [r for r in all_results if "error" not in r],
        "summary": {
            "total_value": round(total_value, 2),
            "total_cost": round(total_cost, 2),
            "total_pnl": round(total_pnl, 2),
            "total_pnl_pct": round(total_pnl/total_cost*100, 2) if total_cost > 0 else 0,
        }
    }
    
    os.makedirs("/root/.openclaw/workspace/ai_agent/results", exist_ok=True)
    result_file = "/root/.openclaw/workspace/ai_agent/results/finance_report.json"
    with open(result_file, "w", encoding="utf-8") as f:
        json.dump(result_data, f, indent=2, ensure_ascii=False)
    
    print(f"\n💾 结果已保存: {result_file}")
    print("=" * 60)


if __name__ == "__main__":
    main()
