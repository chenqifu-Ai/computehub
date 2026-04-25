#!/usr/bin/env python3
"""
DeepSeek-V3.1 671B 全面深度测试 v2
维度：逻辑推理、数学、代码、知识、语言、安全、系统设计、多语言
"""
import json, time, re, sys
import subprocess

results = {}  # 由小智人工验证后填入
notes = {}    # 备注

T = {}  # 存放题目

# ──────── 维度1: 深度逻辑推理 (5题) ────────
T["L1"] = "有100盏灯，初始全部关闭。第1轮切换所有灯的开关，第2轮切换编号为2的倍数的灯，第3轮切换编号为3的倍数的灯...直到第100轮。最后亮着的灯有多少盏？为什么？"
T["L2"] = "甲、乙、丙三人中只有一人说真话。甲说：\"不是我做的。\"乙说：\"是丙做的。\"丙说：\"不是我做的。\"请问是谁做的？逐步推理。"
T["L3"] = "一个岛上，骑士只说真话，无赖只说假话。你遇到A和B。A说：\"我们俩都是无赖。\"B说：\"至少有一个是骑士。\"请问A和B各是什么身份？"
T["L4"] = "5个海盗分100枚金币，按资历从高到低依次提议分配方案，超过半数同意（包括自己）则通过，否则提议者被杀死。假设所有海盗都理性且残忍。最资深的第1个海盗应该怎么分才能保证自己利益最大化？"
T["L5"] = "老师告诉学生A和B：有两个大于1的整数，和是S，积是P。老师私下告诉A积P，告诉B和S。A说：我不知道这两个数。B说：我知道你不知道。A说：那我现在知道了。B说：那我也知道了。请问这两个数是什么？"

# ──────── 维度2: 高等数学 (4题) ────────
T["M1"] = "求极限：lim(x→0) (sin x - x) / x³"
T["M2"] = "一个袋子里有3个红球、5个蓝球、2个绿球。不放回地随机取3个球。求：\n(1) 取到3种颜色各1个的概率\n(2) 取到至少2个红球的概率"
T["M3"] = "矩阵 A = [[2, 1], [1, 2]]，求A的特征值和特征向量。"
T["M4"] = "用数学归纳法证明：1³ + 2³ + 3³ + ... + n³ = [n(n+1)/2]²"

# ──────── 维度3: 复杂代码 (5题) ────────
T["C1"] = "用Python实现一个LRU缓存类，支持get(key)和put(key, value)操作，时间复杂度O(1)。要求写完整的类实现。"
T["C2"] = "实现一个函数 decode_string(s)，将编码字符串解码。编码规则：k[encoded_string]表示重复k次。\n示例：'3[a2[c]]' → 'accaccacc', '2[abc]3[cd]ef' → 'abcabccdcdcdef'"
T["C3"] = "用Python实现一个线程安全的生产者-消费者队列，支持多生产者多消费者场景。写完整代码。"
T["C4"] = "用Python实现一个简单的REST API服务器（使用内置模块），提供/tasks的增删改查接口，数据用内存存储。"
T["C5"] = "给定一个未排序的整数数组，找出最长连续序列的长度。要求O(n)时间复杂度。\n示例：[100,4,200,1,3,2] → 4（因为最长连续序列是[1,2,3,4]）"

# ──────── 维度4: 深度知识 (4题) ────────
T["K1"] = "详细解释TCP三次握手和四次挥手的过程，包括每个状态转换。为什么建立连接是三次而不是两次？为什么断开连接是四次？"
T["K2"] = "解释CAP定理。在分布式系统中，什么是最终一致性？请用实际例子说明。"
T["K3"] = "什么是梯度消失和梯度爆炸？它们在深度学习中如何产生？列举至少3种缓解方法并解释原理。"
T["K4"] = "解释操作系统的虚拟内存机制。什么是页表、TLB、缺页中断？页面置换算法有哪些？比较FIFO、LRU、Clock算法的优劣。"

# ──────── 维度5: 代码修复/安全 (3题) ────────
T["S1"] = "找出以下代码中至少3个安全漏洞并修复：\n\ndef login(username, password):\n    conn = sqlite3.connect('users.db')\n    cursor = conn.cursor()\n    query = f\"SELECT * FROM users WHERE username='{username}' AND password='{password}'\"\n    cursor.execute(query)\n    user = cursor.fetchone()\n    if user:\n        return redirect('/dashboard')\n    else:\n        return 'Login failed'\n\ndef save_file(file):\n    filename = file.filename\n    file.save('/uploads/' + filename)\n    return 'File uploaded'"
T["S2"] = "以下代码有什么问题？如何改进？\n\nimport threading\nbalance = 0\n\ndef withdraw(amount):\n    global balance\n    for i in range(100000):\n        balance -= amount\n\ndef deposit(amount):\n    global balance\n    for i in range(100000):\n        balance += amount\n\nthread1 = threading.Thread(target=withdraw, args=(1,))\nthread2 = threading.Thread(target=deposit, args=(1,))\nthread1.start()\nthread2.start()\nthread1.join()\nthread2.join()\nprint(balance)  # 应该输出0，但往往不是"
T["S3"] = "一个Web应用使用JWT做认证，以下是token验证代码，找出漏洞：\n\ndef verify_token(token):\n    try:\n        payload = jwt.decode(token, options={\"verify_signature\": False})\n        # 或使用 jwt.decode(token, 'secret', algorithms=['none'])\n        username = payload['username']\n        return get_user(username)\n    except:\n        return None"

# ──────── 维度6: 系统设计 (3题) ────────
T["D1"] = "设计一个短链接服务（如bit.ly）。请描述：\n(1) 数据结构设计\n(2) 短链接生成算法\n(3) 重定向流程\n(4) 如何处理高并发\n(5) 如何做数据分片"
T["D2"] = "设计一个分布式缓存系统，要求支持缓存淘汰、过期、集群扩展。请描述整体架构和关键实现细节。"
T["D3"] = "设计一个实时聊天系统（类似微信），支持单聊和群聊。请从架构、数据存储、消息投递、在线状态等方面描述。"

# ──────── 维度7: 中文高级 (3题) ────────
T["Z1"] = "分析以下句子中的歧义并解释原因：\n\"咬死了猎人的狗\"\n\"鸡不吃了\"\n\"冬天能穿多少穿多少，夏天能穿多少穿多少\""
T["Z2"] = "写一首七言绝句，主题是\"AI与人类共创未来\"。要求押韵、对仗工整。"
T["Z3"] = "解释\"薛定谔的猫\"思想实验，然后用这个比喻来描述一个软件开发中的场景。"

# ──────── 维度8: 多语言代码 (3题) ────────
T["X1"] = "用Go写一个并发的Web爬虫，输入一个URL列表，并发抓取并统计每个页面的标题长度。使用goroutine和channel。"
T["X2"] = "用Rust写一个单链表，支持push、pop、reverse操作。包含完整的结构体定义和实现。"
T["X3"] = "用Java写一个线程安全的单例模式，要求懒加载和高性能。给出至少两种实现方式并比较优劣。"

# ──────── 打印所有题目 ────────
def print_all(Q, label):
    print(f"\n\n{'#' * 60}")
    print(f"# 📌 {label}")
    print(f"{'#' * 60}")
    for k, v in Q.items():
        print(f"\n{'─' * 50}")
        print(f"  {k}: {v[:120]}")
        print(f"{'─' * 50}")

if __name__ == "__main__":
    print("=" * 60)
    print("🔬 DeepSeek-V3.1 671B 全面深度测试 v2")
    print("=" * 60)
    all_questions = {
        **{f"L{i}": v for i, (k, v) in enumerate(T.items()) if k.startswith("L")},
        **{f"M{i}": v for i, (k, v) in enumerate(T.items()) if k.startswith("M")},
        **{f"C{i}": v for i, (k, v) in enumerate(T.items()) if k.startswith("C")},
        **{f"K{i}": v for i, (k, v) in enumerate(T.items()) if k.startswith("K")},
        **{f"S{i}": v for i, (k, v) in enumerate(T.items()) if k.startswith("S")},
        **{f"D{i}": v for i, (k, v) in enumerate(T.items()) if k.startswith("D")},
        **{f"Z{i}": v for i, (k, v) in enumerate(T.items()) if k.startswith("Z")},
        **{f"X{i}": v for i, (k, v) in enumerate(T.items()) if k.startswith("X")},
    }
    print(f"\n📋 共 {len(all_questions)} 题 | 8 大维度")
    print(f"⏰ 时间: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"\n{'═' * 60}")

    # 按维度展示
    categories = [
        ("🧠 1. 深度逻辑推理", [T["L1"], T["L2"], T["L3"], T["L4"], T["L5"]]),
        ("📐 2. 高等数学", [T["M1"], T["M2"], T["M3"], T["M4"]]),
        ("💻 3. 复杂代码", [T["C1"], T["C2"], T["C3"], T["C4"], T["C5"]]),
        ("🌐 4. 深度知识", [T["K1"], T["K2"], T["K3"], T["K4"]]),
        ("🔒 5. 代码修复/安全", [T["S1"], T["S2"], T["S3"]]),
        ("🏗️ 6. 系统设计", [T["D1"], T["D2"], T["D3"]]),
        ("📝 7. 中文高级", [T["Z1"], T["Z2"], T["Z3"]]),
        ("🌍 8. 多语言代码", [T["X1"], T["X2"], T["X3"]]),
    ]

    for cat_name, questions in categories:
        print(f"\n{'═' * 60}")
        print(f"  {cat_name}")
        print(f"{'═' * 60}")
        for q in questions:
            short = q.replace('\n', ' ')[:150]
            print(f"  · {short}...")
        print()

    print(f"\n{'═' * 60}")
    print(f"共 30 题，老大可以直接在聊天中说 '全答' 我一次性搞定。")
    print(f"或者按维度来，比如 '先测逻辑'、'测代码'。")
    print(f"{'═' * 60}")
