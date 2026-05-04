#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Qwen 3.6 35B API 连通性和响应
"""

import requests
import json
import sys
from datetime import datetime

API_URL = "http://58.23.129.98:8000/v1"
API_KEY = "78sadn09bjawde123e"
MODEL = "qwen3.6-35b"

def test_api():
    results = []
    
    # 测试 1: 基础连通性
    print("=" * 50)
    print("🧪 Qwen 3.6 35B API 测试")
    print("=" * 50)
    
    # 测试 1: GET 根路径
    print("\n📡 测试 1: 基础连通性 (GET /v1)")
    try:
        resp = requests.get(f"{API_URL}/v1", timeout=10)
        print(f"  状态码: {resp.status_code}")
        print(f"  响应: {resp.text[:200]}")
        if resp.status_code == 200:
            print("  ✅ 连通性 OK")
            results.append(("连通性", "✅ OK", datetime.now().isoformat()))
        else:
            print("  ❌ 连通性异常")
            results.append(("连通性", f"❌ 状态码 {resp.status_code}", datetime.now().isoformat()))
    except Exception as e:
        print(f"  ❌ 连接失败: {e}")
        results.append(("连通性", f"❌ {str(e)}", datetime.now().isoformat()))
    
    # 测试 2: 模型列表
    print("\n📋 测试 2: 获取模型列表")
    try:
        headers = {"Authorization": f"Bearer {API_KEY}"}
        resp = requests.get(f"{API_URL}/v1/models", headers=headers, timeout=10)
        print(f"  状态码: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            models = data.get("data", [])
            for m in models:
                mid = m.get("id", "未知")
                print(f"  - {mid}")
                if mid == MODEL:
                    print(f"  ✅ 目标模型 '{MODEL}' 可用")
                    results.append(("模型发现", f"✅ 找到 {MODEL}", datetime.now().isoformat()))
            if not any("✅" in r[1] for r in results if r[0] == "模型发现"):
                print(f"  ⚠️  未找到 '{MODEL}' 但服务正常")
                results.append(("模型发现", f"⚠️ 服务正常但未找到 {MODEL}", datetime.now().isoformat()))
        else:
            print(f"  ❌ 获取模型列表失败: {resp.text[:200]}")
            results.append(("模型列表", f"❌ 状态码 {resp.status_code}", datetime.now().isoformat()))
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")
        results.append(("模型列表", f"❌ {str(e)}", datetime.now().isoformat()))
    
    # 测试 3: 聊天补全
    print(f"\n💬 测试 3: 聊天补全测试 (模型: {MODEL})")
    try:
        headers = {
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": MODEL,
            "messages": [
                {"role": "system", "content": "你是一个简洁的测试助手。"},
                {"role": "user", "content": "你好，请回复'测试成功'并说一句话。"}
            ],
            "max_tokens": 100,
            "temperature": 0.7
        }
        resp = requests.post(f"{API_URL}/v1/chat/completions", headers=headers, json=payload, timeout=60)
        print(f"  状态码: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            content = data["choices"][0]["message"]["content"]
            print(f"  回复: {content}")
            if "测试成功" in content or "测试" in content:
                print("  ✅ 聊天补全正常")
                results.append(("聊天补全", "✅ 正常响应", datetime.now().isoformat()))
            else:
                print("  ⚠️  响应不太规范但正常")
                results.append(("聊天补全", "⚠️ 响应格式需改进", datetime.now().isoformat()))
        else:
            print(f"  ❌ 聊天补全失败: {resp.text[:200]}")
            results.append(("聊天补全", f"❌ 状态码 {resp.status_code}", datetime.now().isoformat()))
    except Exception as e:
        print(f"  ❌ 请求失败: {e}")
        results.append(("聊天补全", f"❌ {str(e)}", datetime.now().isoformat()))
    
    # 总结
    print("\n" + "=" * 50)
    print("📊 测试结果汇总")
    print("=" * 50)
    
    all_pass = all("✅" in r[1] for r in results)
    for name, status, time_str in results:
        icon = "✅" if "✅" in status else "❌" if "❌" in status else "⚠️"
        print(f"  {icon} {name}: {status}")
    
    if all_pass:
        print("\n🎉 全部测试通过！API 配置可用。")
    else:
        failed = [r for r in results if "❌" in r[1]]
        if failed:
            print(f"\n⚠️ {len(failed)} 项测试未通过")
    
    # 保存结果
    result_file = "/root/.openclaw/workspace/expert_work_logs/api_test_result_20260423_1102.json"
    with open(result_file, 'w', encoding='utf-8') as f:
        json.dump({
            "test_time": datetime.now().isoformat(),
            "api_url": API_URL,
            "model": MODEL,
            "results": {r[0]: {"status": r[1], "time": r[2]} for r in results}
        }, f, ensure_ascii=False, indent=2)
    print(f"\n💾 结果已保存: {result_file}")
    
    return all_pass

if __name__ == "__main__":
    success = test_api()
    sys.exit(0 if success else 1)
