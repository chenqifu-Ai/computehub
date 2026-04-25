#!/usr/bin/env python3
"""
任务路由分发系统 (Task Router)
================================
大模型(大脑) → 拆分任务 → 小模型(手脚)并行执行 → 大模型汇总

架构:
┌─────────────────────────────────────────────┐
│                大模型 (Coordinator)           │
│          负责: 拆解任务 + 整合结果            │
└────┬────────────────────────────┬───────────┘
     │ 分解                        │ 汇总
┌────▼────┐ ┌────▼────┐ ... ┌────▼────┐
│ 小模型1 │ │ 小模型2 │     │ 小模型N │
│ 专精A   │ │ 专精B   │     │ 专精N   │
└─────────┘ └─────────┘     └─────────┘
"""

import json
import time
import urllib.request
import re
from datetime import datetime

# ==================== 配置 ====================

COORDINATOR = {
    "base_url": "http://58.23.129.98:8000/v1/chat/completions",
    "model": "qwen3.6-35b",
    "api_key": "sk-78sadn09bjawde123e"
}

WORKER_POOL = [
    {
        "id": "worker_qwen",
        "base_url": "http://58.23.129.98:8000/v1/chat/completions",
        "model": "qwen3.6-35b",
        "api_key": "sk-78sadn09bjawde123e",
        "expertise": ["编程", "数据分析", "技术文档"]
    },
    {
        "id": "worker_ollama",
        "base_url": "https://ollama.com/v1/chat/completions",
        "model": "deepseek-v4-flash",
        "api_key": "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii",
        "expertise": ["推理", "数学", "逻辑"]
    },
    {
        "id": "worker_glm51",
        "base_url": "https://ollama.com/v1/chat/completions",
        "model": "glm-5.1",
        "api_key": "8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii",
        "expertise": ["编程", "软件工程", "代码审查", "技术文档"]
    }
]


def call_llm(base_url, api_key, messages, model, max_tokens=2000, temperature=0.7):
    """调用 LLM API"""
    payload = {
        "model": model,
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        base_url, data=data,
        headers={"Content-Type": "application/json",
                 "Authorization": "Bearer " + api_key},
        method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            msg = body["choices"][0]["message"]
            content = msg.get("content") or ""
            reasoning = msg.get("reasoning") or ""
            # 两个字段拼接（Qwen: content=null, reasoning=全部）
            return reasoning + content or content or ""
    except Exception as e:
        return "[ERROR] API调用失败: " + str(e)


def extract_json(text):
    """
    从文本中提取JSON。
    Qwen/Ollama模型回答全在reasoning字段，开头是大段自然语言思考，
    JSON对象在后面。策略：找到最后一个完整的JSON对象。
    """
    # 策略1: 找所有 {} 块，从后往前找能解析的
    # 找到所有可能的JSON起始位置（紧跟: "subtasks" 或 "original_task"）
    json_start_patterns = [
        r'\{\s*"original_task"',
        r'\{\s*"subtasks"',
    ]

    candidates = []
    for pat in json_start_patterns:
        for m in re.finditer(pat, text):
            start = m.start()
            # 从此处向后找匹配的 }
            brace_count = 0
            end = -1
            for i in range(start, len(text)):
                if text[i] == '{':
                    brace_count += 1
                elif text[i] == '}':
                    brace_count -= 1
                    if brace_count == 0:
                        end = i + 1
                        break
            if end > 0:
                candidates.append((start, end, text[start:end]))

    # 从后往前找第一个能解析成功的
    for start, end, candidate in sorted(candidates, key=lambda x: -x[0]):
        try:
            parsed = json.loads(candidate)
            return parsed, candidate
        except json.JSONDecodeError:
            continue

    # 策略2: 找最大的 {} 块
    first_brace = text.find('{')
    if first_brace >= 0:
        brace_count = 0
        end = -1
        for i in range(first_brace, len(text)):
            if text[i] == '{':
                brace_count += 1
            elif text[i] == '}':
                brace_count -= 1
                if brace_count == 0:
                    end = i + 1
                    break
        if end > 0:
            try:
                return json.loads(text[first_brace:end]), text[first_brace:end]
            except json.JSONDecodeError:
                pass

    return None, text


class TaskRouter:
    """任务路由分发系统"""

    def __init__(self, coordinator=None, worker_pool=None):
        self.coordinator = coordinator or COORDINATOR
        self.worker_pool = worker_pool or WORKER_POOL
        self.task_history = []
        self.stats = {
            "total_tasks": 0,
            "successful_tasks": 0,
            "failed_tasks": 0,
            "total_time": 0
        }

    def _match_worker(self, expertise):
        if not expertise:
            return self.worker_pool[0]
        best = None
        best_score = 0
        for w in self.worker_pool:
            score = sum(1 for e in w.get("expertise", [])
                        if e in expertise or expertise in e)
            if score > best_score:
                best_score = score
                best = w
        return best or self.worker_pool[0]

    def decompose_task(self, main_task):
        """大模型拆解任务"""
        print("\n🧠 [Coordinator] 正在拆解任务...")
        print("   使用模型: " + self.coordinator["model"])

        # 强调纯JSON输出，避免思考文本
        prompt = ("你是一个任务拆解专家。将以下任务拆解成5个独立小任务。\n\n"
                  "【强制】只输出JSON对象，不要任何解释、思考、Markdown格式。\n"
                  "【强制】以{开头，以}结尾。\n\n"
                  "主任务：" + main_task + "\n\n"
                  "JSON格式：\n"
                  '{"original_task":"MAIN_TASK","subtasks":[{"id":1,"description":"描述","expertise":"能力","instructions":"指令"}]}'
                  )

        messages = [{"role": "user", "content": prompt}]
        result = call_llm(
            self.coordinator["base_url"],
            self.coordinator["api_key"],
            messages,
            self.coordinator["model"],
            max_tokens=4000
        )

        parsed, raw = extract_json(result)
        if parsed is None:
            print("❌ 没有提取到有效JSON")
            print("  前200字: " + result[:200])
            return []

        subtasks = []
        for task in parsed.get("subtasks", []):
            assigned = self._match_worker(task.get("expertise", ""))
            subtasks.append({
                "id": task.get("id", len(subtasks) + 1),
                "description": task.get("description", ""),
                "expertise": task.get("expertise", ""),
                "instructions": task.get("instructions", ""),
                "assigned_worker": assigned
            })

        print("✅ 拆解完成，生成 " + str(len(subtasks)) + " 个子任务")
        for s in subtasks:
            print("   [" + str(s["id"]) + "] " + s["description"])
            print("       → " + s["assigned_worker"]["id"])

        return subtasks

    def execute_subtask(self, subtask):
        """执行单个子任务"""
        w = subtask["assigned_worker"]
        tid = subtask["id"]

        print("\n🔧 [" + w["id"] + "] 执行任务 [" + str(tid) + "]: " + subtask["description"])
        print("   模型: " + w["model"])

        prompt = ("你是" + subtask["expertise"] + "专家。任务：" +
                  subtask["description"] + "\n指令：" +
                  subtask["instructions"] +
                  "\n要求：只返回结果，不要解释。")

        messages = [{"role": "user", "content": prompt}]
        t0 = time.time()
        result = call_llm(w["base_url"], w["api_key"], messages,
                          w["model"], max_tokens=2000)
        elapsed = round(time.time() - t0, 2)
        success = not result.startswith("[ERROR]")

        self.stats["total_tasks"] += 1
        if success:
            self.stats["successful_tasks"] += 1
            status = "✅"
        else:
            self.stats["failed_tasks"] += 1
            status = "❌"
        self.stats["total_time"] += elapsed

        record = {
            "task_id": tid,
            "description": subtask["description"],
            "worker": w["id"],
            "model": w["model"],
            "result": result[:500],
            "elapsed": elapsed,
            "status": status
        }
        self.task_history.append(record)

        print("   " + status + " 完成 (" + str(elapsed) + "s)")
        if result:
            print("   结果: " + result[:100])
        return record

    def aggregate_results(self, subtasks, task_records):
        """大模型整合结果"""
        print("\n🧠 [Coordinator] 正在整合结果...")

        agg = ("你是信息整合专家。整合以下结果，给出最终答案。\n\n主任务：")
        if subtasks:
            agg += subtasks[0]["description"]
        agg += "\n\n执行结果：\n"
        for r in task_records:
            agg += ("任务[" + str(r["task_id"]) + "]:" + r["description"] +
                    "\n模型:" + r["model"] + "\n结果:" + r["result"][:200] + "\n\n")
        agg += "\n要求：综合所有结果，给出结构化最终答案。"

        messages = [{"role": "user", "content": agg}]
        return call_llm(
            self.coordinator["base_url"],
            self.coordinator["api_key"],
            messages,
            self.coordinator["model"],
            max_tokens=4000
        )

    def run(self, main_task):
        """主流程: 拆解 → 分发 → 执行 → 整合"""
        print("=" * 60)
        print("  任务路由分发系统 (Task Router)")
        print("=" * 60)
        print("\n主任务: " + main_task)
        print("Worker池: " + str([w["id"] for w in self.worker_pool]))

        t0 = time.time()

        # Step 1: 拆解
        subtasks = self.decompose_task(main_task)
        if not subtasks:
            print("❌ 任务拆解失败，无法继续")
            return None

        # Step 2: 执行
        print("\n🚀 开始执行子任务...")
        task_records = []
        for s in subtasks:
            r = self.execute_subtask(s)
            task_records.append(r)

        # Step 3: 整合
        final = self.aggregate_results(subtasks, task_records)

        elapsed = round(time.time() - t0, 2)

        # 统计
        print("\n" + "=" * 60)
        print("  执行统计")
        print("=" * 60)
        print("总任务: " + str(self.stats["total_tasks"]))
        print("成功: " + str(self.stats["successful_tasks"]))
        print("失败: " + str(self.stats["failed_tasks"]))
        print("总耗时: " + str(elapsed) + "s")

        print("\n📋 子任务执行记录:")
        for r in task_records:
            print("  " + r["status"] + " [" + str(r["task_id"]) + "] " + r["description"][:30])
            print("      " + r["model"] + " | " + str(r["elapsed"]) + "s")

        print("\n" + "=" * 60)
        print("  最终答案")
        print("=" * 60)
        print(final)

        return {
            "main_task": main_task,
            "subtasks": subtasks,
            "task_records": task_records,
            "final_result": final,
            "stats": self.stats,
            "elapsed": elapsed
        }


def main():
    router = TaskRouter()

    print("\n📝 示例：AI领域新闻分析")
    print("-" * 40)

    main_task = ("分析并总结最近一周AI领域的重大新闻，"
                 "包括英文原文、中文翻译、关键要点，"
                 "以及对中国市场的影响分析")

    result = router.run(main_task)
    return result

if __name__ == "__main__":
    main()
