#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
qwen3.6-35b 全面测试 v10
=========================
基于 v1-v9 历史数据重新设计，覆盖全面且针对性强

v1: 43% | v2: 43% | v3: 81% 🥇 | v4: 86% 🥇 | v5: 71% 🥈 | v6: 57% ❌ | v7: 53% ❌ | v8: 68% 🥉
目标: 突破86分，验证v4巅峰表现是否可复现
"""

import json
import time
import sys
import os
import re

import importlib.util
spec = importlib.util.spec_from_file_location("qwen36_adapter", "/root/.openclaw/workspace/ai_agent/config/qwen36_adapter.py")
qwen36_adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(qwen36_adapter)
Qwen36Adapter = qwen36_adapter.Qwen36Adapter

adapter = Qwen36Adapter()

results = []
total_start = time.time()

def test(name, category, prompt, criteria, system=None):
    """执行一个测试项"""
    start = time.time()
    try:
        if "代码生成" in category:
            answer = adapter.ask_code(prompt)
        elif "深度" in category or "推理" in category:
            r = adapter.ask_detailed(prompt, system)
            answer = r["answer"]
        else:
            answer = adapter.ask(prompt, system)
        elapsed = time.time() - start
        
        # 评估
        passed = False
        detail = ""
        
        if callable(criteria):
            passed, detail = criteria(answer)
        elif isinstance(criteria, dict):
            # 多条件评估
            for criterion_name, criterion_func in criteria.items():
                ok, det = criterion_func(answer)
                if ok:
                    passed = True
                    detail = criterion_name
                    break
            if not passed:
                # 取最后一个失败原因
                for criterion_name, criterion_func in criteria.items():
                    ok, det = criterion_func(answer)
                    if not ok:
                        detail = f"{criterion_name}: {det}"
        else:
            # 简单关键词匹配
            criteria_list = criteria if isinstance(criteria, list) else [criteria]
            for c in criteria_list:
                if c in answer:
                    passed = True
                    detail = c
                    break
            if not passed:
                detail = f"未匹配任何期望关键词"
        
        # 截断详情
        if len(detail) > 300:
            detail = detail[:300] + "..."
        
        results.append({
            "name": name,
            "category": category,
            "passed": passed,
            "answer_preview": answer[:200],
            "detail": detail,
            "time": round(elapsed, 2),
        })
        
        status = "✅" if passed else "❌"
        print(f"  {status} [{category}] {name} ({elapsed:.1f}s)")
        if not passed:
            print(f"     详情: {detail[:150]}")
        
        return passed
    except Exception as e:
        elapsed = time.time() - start
        results.append({
            "name": name,
            "category": category,
            "passed": False,
            "answer_preview": "",
            "detail": f"异常: {str(e)[:200]}",
            "time": round(elapsed, 2),
        })
        print(f"  ❌ [{category}] {name} ({elapsed:.1f}s) - 异常: {str(e)[:100]}")
        return False


# ==================== 第一部分：语言与常识 (10题) ====================
print("\n" + "="*70)
print("📝 第一部分：语言与常识 (10题)")
print("="*70)

def check_contains_or_relevant(expected_keywords, min_len=10):
    """检查是否包含期望关键词或相关内容"""
    def checker(answer):
        # 检查长度
        if len(answer) < min_len:
            return False, f"回答过短({len(answer)}字)"
        # 检查关键词
        for kw in expected_keywords:
            if kw in answer:
                return True, f"包含关键词'{kw}'"
        return False, "未匹配任何期望内容"
    return checker

# 1. 中文理解
def t1_criterion(answer):
    if "20" in answer or "二十" in answer:
        return True, "正确回答20"
    # 也可能回答了计算过程
    if "4*5" in answer or "4×5" in answer or "20" in answer:
        return True, "给出正确答案20"
    return False, f"回答: {answer[:100]}"

test("中文乘法", "语言", "5乘以4等于多少？", t1_criterion)

# 2. 成语
test("成语填空", "语言", "请填写成语：守株待__", 
     lambda a: (True, "正确") if "兔" in a else (False, f"未找到'兔': {a[:100]}"))

# 3. 诗词
test("古诗词", "语言", "请默写《静夜思》", 
     lambda a: (True, "包含静夜思内容") if any(k in a for k in ["床前明月光", "疑是地上霜", "举头望明月"]) else (False, f"未找到: {a[:80]}"))

# 4. 阅读理解
def t4_criterion(answer):
    if "西红柿" in answer or "番茄" in answer:
        return True, "识别西红柿是水果"
    if "蔬菜" in answer and ("错误" in answer or "不对" in answer):
        return True, "判断蔬菜说法错误"
    return False, f"回答: {answer[:150]}"

test("阅读理解", "语言", "小红说'西红柿是蔬菜'，她对吗？", t4_criterion)

# 5. 语言知识
test("语言知识", "语言", "中文里'他'和'她'的区别是什么？", 
     lambda a: (True, "说明性别区分") if "男" in a and "女" in a else (False, f"{a[:100]}"))

# 6. 类比推理
def t6_criterion(answer):
    # 手 : 手套 = 脚 : 袜子
    if any(k in answer for k in ["袜子", "socks", "袜子", "袜"]):
        return True, "正确回答袜子"
    return False, f"回答: {answer[:100]}"

test("类比推理", "语言", "手和手套的关系，相当于脚和什么的关系？", t6_criterion)

# 7. 常识
test("常识", "语言", "人体最大的器官是什么？",
     lambda a: (True, "皮肤") if "皮肤" in a else (False, f"回答: {a[:100]}"))

# 8. 逻辑推理
def t8_criterion(answer):
    # 如果有3个苹果，吃了1个，还剩2个
    if "2" in answer:
        return True, "正确回答2个"
    return False, f"回答: {answer[:100]}"

test("逻辑推理", "语言", "你有3个苹果，吃了1个，还剩几个？", t8_criterion)

# 9. 翻译
test("翻译", "语言", "把'Hello, how are you?'翻译成中文", 
     lambda a: (True, "你好") if "你好" in a else (False, f"回答: {a[:80]}"))

# 10. 文字游戏
test("文字游戏", "语言", "' abcdefg '倒过来怎么写？",
     lambda a: (True, "gfedcba") if "gfedcba" in a else (False, f"回答: {a[:100]}"))


# ==================== 第二部分：数学与科学 (8题) ====================
print("\n" + "="*70)
print("📝 第二部分：数学与科学 (8题)")
print("="*70)

# 11. 基础数学
test("基础数学", "数学", "计算: 15 × 28 = ?",
     lambda a: (True, "420") if "420" in a else (False, f"回答: {a[:100]}"))

# 12. 代数
def t12_criterion(answer):
    # x + 2x = 3x
    if "3x" in answer:
        return True, "3x"
    if any(k in answer for k in ["3x", "3 * x", "3 *x", "3x"]):
        return True, "3x"
    return False, f"回答: {answer[:100]}"

test("代数", "数学", "x + 2x 等于多少？", t12_criterion)

# 13. 百分比
def t13_criterion(answer):
    # 200的25% = 50
    if "50" in answer:
        return True, "50"
    return False, f"回答: {answer[:100]}"

test("百分比", "数学", "200的25%是多少？", t13_criterion)

# 14. 几何
def t14_criterion(answer):
    # 正方形面积 = 边长²
    if any(k in answer for k in ["16", "16", "64"]):
        # 边长4 → 面积16；边长8 → 面积64
        return True, "给出面积"
    return False, f"回答: {answer[:100]}"

test("几何", "数学", "一个正方形边长为4，面积是多少？", t14_criterion)

# 15. 物理 - 修正：不问公式，问具体计算
def t15_criterion(answer):
    # F = ma = 2 * 10 = 20N
    if "20" in answer and ("N" in answer or "牛" in answer or "牛顿" in answer):
        return True, "20N"
    return False, f"回答: {answer[:100]}"

test("物理计算", "科学", "一个质量为2kg的物体，受到10m/s²的加速度，合力是多少牛顿？", t15_criterion)

# 16. 化学
test("化学", "科学", "水的化学式是什么？",
     lambda a: (True, "H2O") if "H2O" in a else (False, f"回答: {a[:80]}"))

# 17. 天文
def t17_criterion(answer):
    if "8" in answer and ("分钟" in answer or "min" in answer or "光" in answer):
        return True, "8分钟"
    return False, f"回答: {answer[:100]}"

test("天文", "科学", "太阳光到达地球大约需要多久？", t17_criterion)

# 18. 概率
def t18_criterion(answer):
    # 抛硬币正面概率 = 1/2 = 0.5 = 50%
    if any(k in answer for k in ["1/2", "0.5", "50%", "二分之一", "一半"]):
        return True, "概率正确"
    return False, f"回答: {answer[:100]}"

test("概率", "数学", "抛一枚硬币，出现正面的概率是多少？", t18_criterion)


# ==================== 第三部分：编程基础 (8题) ====================
print("\n" + "="*70)
print("📝 第三部分：编程基础 (8题) - 代码生成+概念")
print("="*70)

# 19. Python列表
def t19_criterion(answer):
    if "append" in answer or "extend" in answer:
        return True, "使用append/extend"
    if "[] + []" in answer or "列表拼接" in answer:
        return True, "列表拼接"
    return False, f"回答: {answer[:150]}"

test("Python列表", "编程", "Python中如何合并两个列表 a=[1,2] 和 b=[3,4]？", t19_criterion)

# 20. 字典操作
def t20_criterion(answer):
    if "dict" in answer or "字典" in answer:
        return True, "提到字典结构"
    return False, f"回答: {answer[:100]}"

test("字典结构", "编程", "Python中{'name': 'Alice', 'age': 25}是什么数据结构？", t20_criterion)

# 21. 循环
def t21_criterion(answer):
    if "for" in answer and "range" in answer:
        return True, "for+range循环"
    return False, f"回答: {answer[:100]}"

test("for循环", "编程", "Python中如何打印0到9？",
     lambda a: (True, "range(10)") if "range" in a else (False, f"回答: {a[:100]}"))

# 22. 异常处理
def t22_criterion(answer):
    if "try" in answer and "except" in answer:
        return True, "try-except"
    return False, f"回答: {answer[:100]}"

test("异常处理", "编程", "Python中如何捕获除零错误？", t22_criterion)

# 23. 函数定义
test("函数定义", "编程", "Python中如何定义一个函数？",
     lambda a: (True, "def") if "def " in a else (False, f"回答: {a[:80]}"))

# 24. 面向对象
def t24_criterion(answer):
    if "class" in answer and "self" in answer:
        return True, "class+self"
    return False, f"回答: {answer[:150]}"

test("类定义", "编程", "Python中如何定义一个类？", t24_criterion)

# 25. 字符串操作
def t25_criterion(answer):
    if "split" in answer or "strip" in answer or "replace" in answer:
        return True, "字符串方法"
    return False, f"回答: {answer[:100]}"

test("字符串操作", "编程", "Python中如何把一个逗号分隔的字符串转成列表？", t25_criterion)

# 26. 列表推导式
test("列表推导式", "编程", "Python中如何用一行代码生成[1,4,9,16,25]？",
     lambda a: (True, "[x*x") if "[x*x" in a or "[i*i" in a or "[n*n" in a else (False, f"回答: {a[:100]}"))


# ==================== 第四部分：计算机网络 (6题) ====================
print("\n" + "="*70)
print("📝 第四部分：计算机网络 (6题)")
print("="*70)

# 27. OSI模型
def t27_criterion(answer):
    layers = ["物理层", "数据链路层", "网络层", "传输层", "会话层", "表示层", "应用层"]
    count = sum(1 for l in layers if l in answer)
    if count >= 5:
        return True, f"列出{count}/7层"
    return False, f"只列出{count}/7层: {answer[:150]}"

test("OSI七层模型", "网络", "请列出OSI七层模型的名称", t27_criterion)

# 28. HTTP状态码
def t28_criterion(answer):
    if "200" in answer and "404" in answer and "500" in answer:
        return True, "包含200/404/500"
    if "200" in answer and ("成功" in answer or "OK" in answer):
        return True, "200状态码"
    return False, f"回答: {answer[:150]}"

test("HTTP状态码", "网络", "HTTP 200、404、500分别代表什么？", t28_criterion)

# 29. TCP/UDP
def t29_criterion(answer):
    if ("可靠" in answer or "连接" in answer) and ("不可靠" in answer or "无连接" in answer):
        return True, "TCP可靠连接 UDP不可靠"
    return False, f"回答: {answer[:150]}"

test("TCP vs UDP", "网络", "TCP和UDP的主要区别是什么？", t29_criterion)

# 30. DNS
def t30_criterion(answer):
    if "域名" in answer and ("IP" in answer or "地址" in answer):
        return True, "域名解析为IP"
    return False, f"回答: {answer[:100]}"

test("DNS原理", "网络", "DNS的作用是什么？", t30_criterion)

# 31. SSL/TLS
def t31_criterion(answer):
    if "加密" in answer and ("传输" in answer or "通信" in answer):
        return True, "加密传输"
    return False, f"回答: {answer[:100]}"

test("SSL/TLS", "网络", "SSL/TLS的作用是什么？", t31_criterion)

# 32. 跨域
def t32_criterion(answer):
    if "CORS" in answer or "跨域" in answer or "JSONP" in answer:
        return True, "提到跨域解决方案"
    return False, f"回答: {answer[:150]}"

test("跨域问题", "网络", "浏览器跨域问题怎么解决？", t32_criterion)


# ==================== 第五部分：数据库 (4题) ====================
print("\n" + "="*70)
print("📝 第五部分：数据库 (4题)")
print("="*70)

# 33. SQL
def t33_criterion(answer):
    if "SELECT" in answer.upper() or "select" in answer:
        return True, "SELECT语句"
    return False, f"回答: {answer[:100]}"

test("SELECT查询", "数据库", "MySQL中如何查询users表中所有记录？", t33_criterion)

# 34. JOIN
test("JOIN", "数据库", "SQL中INNER JOIN和LEFT JOIN的区别是什么？",
     lambda a: (True, "INNER内连接 LEFT左连接") if ("INNER" in a and "LEFT" in a) or ("内连接" in a and "左连接" in a) else (False, f"回答: {a[:150]}"))

# 35. 索引
def t35_criterion(answer):
    if "索引" in answer and ("加快" in answer or "优化" in answer or "加速" in answer):
        return True, "索引加速查询"
    return False, f"回答: {answer[:100]}"

test("索引", "数据库", "数据库索引的作用是什么？", t35_criterion)

# 36. ACID
test("ACID", "数据库", "数据库事务的ACID特性分别指什么？",
     lambda a: (True, "原子一致性隔离持久") if all(k in a for k in ["原子", "一致", "隔离", "持久"]) else (False, f"回答: {a[:150]}"))


# ==================== 第六部分：操作系统 (4题) ====================
print("\n" + "="*70)
print("📝 第六部分：操作系统 (4题)")
print("="*70)

# 37. 进程vs线程
def t37_criterion(answer):
    if ("进程" in answer and "线程" in answer and 
        ("资源" in answer or "独立" in answer or "内存" in answer)):
        return True, "区分进程线程"
    return False, f"回答: {answer[:150]}"

test("进程vs线程", "系统", "进程和线程的区别是什么？", t37_criterion)

# 38. 内存管理
test("内存管理", "系统", "什么是虚拟内存？",
     lambda a: (True, "虚拟地址" or "映射" or "分页") if "虚拟" in a and ("内存" in a or "地址" in a) else (False, f"回答: {a[:100]}"))

# 39. 死锁
def t39_criterion(answer):
    if "死锁" in answer and ("四个条件" in answer or "互斥" in answer or "_HOLD" in answer or "保持" in answer):
        return True, "提到死锁条件"
    return False, f"回答: {answer[:100]}"

test("死锁", "系统", "什么是死锁？产生死锁的四个必要条件是什么？", t39_criterion)

# 40. Linux命令
test("Linux命令", "系统", "Linux中查看磁盘使用情况的命令是什么？",
     lambda a: (True, "df") if "df" in a else (False, f"回答: {a[:80]}"))


# ==================== 第七部分：软件工程与架构 (4题) ====================
print("\n" + "="*70)
print("📝 第七部分：软件工程与架构 (4题)")
print("="*70)

# 41. 设计模式
def t41_criterion(answer):
    if "设计模式" in answer and len(answer) > 50:
        return True, "提到设计模式"
    return False, f"回答: {answer[:100]}"

test("设计模式", "架构", "什么是设计模式？列举至少3种",
     lambda a: (True, "设计模式") if "设计模式" in a else (False, f"回答: {a[:150]}"))

# 42. 微服务
def t42_criterion(answer):
    if "微服务" in answer and ("服务" in answer and ("拆" in answer or "独立" in answer or "小" in answer)):
        return True, "拆分为小服务"
    return False, f"回答: {answer[:150]}"

test("微服务架构", "架构", "什么是微服务架构？", t42_criterion)

# 43. RESTful API
def t43_criterion(answer):
    if "REST" in answer or "restful" in answer:
        return True, "提到REST"
    if "HTTP" in answer and ("GET" in answer or "POST" in answer) and ("资源" in answer):
        return True, "HTTP+资源"
    return False, f"回答: {answer[:150]}"

test("RESTful", "架构", "什么是RESTful API？", t43_criterion)

# 44. 版本控制
test("Git分支", "架构", "Git中git merge和git rebase的区别？",
     lambda a: (True, "合并历史" or "重写历史") if ("merge" in a or "合并" in a) and ("rebase" in a or "重写" in a) else (False, f"回答: {a[:150]}"))


# ==================== 第八部分：代码生成 (2题) ====================
print("\n" + "="*70)
print("📝 第八部分：代码生成 (2题) - 生成可执行代码")
print("="*70)

# 45. Python生成器
code45 = adapter.ask_code("写一个Python生成器函数，生成斐波那契数列的前n项")
# 验证生成的代码
has_gen = "yield" in code45
has_def = "def " in code45
has_fib = "fib" in code45.lower() or "斐波" in code45 or "fibonacci" in code45.lower()
t45 = has_gen and has_def
details45 = []
if has_gen: details45.append("yield✅")
if has_def: details45.append("def✅")
if has_fib: details45.append("fib✅")
else: details45.append("fib❌")

results.append({
    "name": "代码-斐波那契", "category": "代码生成",
    "passed": t45, "answer_preview": code45[:200],
    "detail": " | ".join(details45), "time": 0
})
status = "✅" if t45 else "❌"
print(f"  {status} [代码生成] 代码-斐波那契 - {' | '.join(details45)}")

# 46. Python装饰器
code46 = adapter.ask_code("写一个Python装饰器，用于记录函数的执行时间")
has_dec = "@" in code46
has_time = "time" in code46.lower() or "时间" in code46
has_def = "def " in code46
t46 = has_dec and has_def
details46 = []
if has_dec: details46.append("@✅")
if has_time: details46.append("time✅")
if has_def: details46.append("def✅")

results.append({
    "name": "代码-装饰器", "category": "代码生成",
    "passed": t46, "answer_preview": code46[:200],
    "detail": " | ".join(details46), "time": 0
})
status = "✅" if t46 else "❌"
print(f"  {status} [代码生成] 代码-装饰器 - {' | '.join(details46)}")


# ==================== 统计 ====================
total_time = time.time() - total_start
passed = sum(1 for r in results if r["passed"])
total = len(results)
score = round(passed / total * 100, 1)
times = [r["time"] for r in results if r["time"] > 0]
avg_time = round(sum(times) / len(times), 2) if times else 0

# 按类别统计
categories = {}
for r in results:
    cat = r["category"]
    if cat not in categories:
        categories[cat] = {"total": 0, "passed": 0}
    categories[cat]["total"] += 1
    if r["passed"]:
        categories[cat]["passed"] += 1

# 判定等级
if score >= 85:
    grade = "🥇 A 优秀"
elif score >= 70:
    grade = "🥈 B 良好"
elif score >= 55:
    grade = "🥉 C 合格"
elif score >= 40:
    grade = "⚠️ D 需改进"
else:
    grade = "❌ E 不合格"

report = {
    "model": "qwen3.6-35b",
    "version": "v10-comprehensive",
    "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S+08:00"),
    "total": total,
    "passed": passed,
    "failed": total - passed,
    "score": score,
    "grade": grade,
    "performance": {
        "avg_time": avg_time,
        "fastest": round(min(times), 2) if times else 0,
        "slowest": round(max(times), 2) if times else 0,
        "total_time": round(total_time, 2),
    },
    "categories": categories,
    "details": [
        {
            "name": r["name"],
            "category": r["category"],
            "passed": r["passed"],
            "detail": r["detail"],
            "time": r["time"],
        }
        for r in results
    ],
    "history": {
        "v1": 43.0,
        "v2": 43.0,
        "v3": 81.0,
        "v4": 86.0,
        "v5": 70.6,
        "v6": 57.1,
        "v7": 53.3,
        "v8": 68.2,
        "v10": score,
    },
}

# 保存报告
save_dir = "/root/.openclaw/workspace/memory/topics/技术经验"
os.makedirs(save_dir, exist_ok=True)
report_path = os.path.join(save_dir, "qwen36-35b-test-v10-comprehensive.json")
with open(report_path, "w", encoding="utf-8") as f:
    json.dump(report, f, ensure_ascii=False, indent=2)

# 输出总结
print("\n" + "="*70)
print(f"📊 qwen3.6-35b 全面测试 v10 总结")
print("="*70)
print(f"  总分: {passed}/{total} ({score}%){grade}")
print(f"  耗时: 平均{avg_time}s | 最快{min(times):.1f}s | 最慢{max(times):.1f}s | 总{total_time:.1f}s")
print(f"\n  分类成绩:")
for cat, stats in sorted(categories.items()):
    pct = round(stats["passed"]/stats["total"]*100, 1)
    bar = "█" * int(pct/5) + "░" * (20 - int(pct/5))
    print(f"    [{cat}] {bar} {stats['passed']}/{stats['total']} ({pct}%)")

print(f"\n  历史记录:")
for ver, s in report["history"].items():
    bar = "█" * int(s/5) + "░" * (20 - int(s/5))
    print(f"    {ver:6s}: {s:5.1f}% {bar}")

print(f"\n  失败项:")
for r in results:
    if not r["passed"]:
        print(f"    ❌ {r['name']}: {r['detail'][:80]}")

print(f"\n  📁 报告保存: {report_path}")
print(f"  ✅ 测试完成")
