#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Last edited by TUI Client: 2026-04-20 10:16:26

"""
AI 智能体框架 - 进化版
实现真实的 LLM 驱动闭环，消除 Mock 逻辑。
"""

import os
import json
import subprocess
import traceback
import requests
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

class AIAgent:
    def __init__(self, name: str = "AI 助手", workspace: str = None):
        self.name = name
        self.workspace = Path(workspace) if workspace else Path.home() / ".openclaw" / "workspace"
        self.task = ""
        self.plan = []
        self.code_history = []
        self.results = []
        self.max_iterations = 10
        self.current_iteration = 0
        
        # API 配置 (从环境变量或配置文件获取，此处为演示绑定)
        self.api_key = "sk-65ca99f6fd55437fba47dc7ba7973242"
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.model = "qwen-max"

        (self.workspace / "ai_agent").mkdir(parents=True, exist_ok=True)
        (self.workspace / "ai_agent" / "code").mkdir(parents=True, exist_ok=True)
        (self.workspace / "ai_agent" / "results").mkdir(parents=True, exist_ok=True)

    def _call_llm(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> str:
        """真实的 LLM API 调用"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "input": {"prompt": f"<|<|imim_start|>system\\n{system_prompt}<|<|imim_end|>\\n<|<|imim_start|>user\\n{prompt}<|<|imim_end|>\\n<|<|imim_start|>assistant\\n"},
            "parameters": {"result_format": "message"}
        }
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            res_json = response.json()
            return res_json['output']['choices'][0]['message']['content']
        except Exception as e:
            print(f"❌ LLM API Error: {e}")
            return f"Error occurred during LLM call: {str(e)}"

    def think(self, task: str) -> Dict:
        print(f"\n{'='*70}\n🧠 思考 (LLM Real-time): {task}\n{'='*70}")
        prompt = f"Task: {task}\nAnalyze the task and provide a JSON response with 'analysis', 'plan' (list of steps), and 'next_step' ('code')."
        system_prompt = "You are a strategic AI planner. Return ONLY pure JSON."
        
        response = self._call_llm(prompt, system_prompt)
        try:
            thought = json.loads(response)
            print(f"📋 计划: {thought.get('plan')}")
            return thought
        except:
            return {"analysis": response, "plan": ["1. Generic execution"], "next_step": "code"}

    def code(self, task: str, context: Dict = None) -> str:
        print(f"\n{'='*70}\n💻 编写代码 (LLM Real-time)\n{'='*70}")
        prompt = f"Task: {task}\nContext: {context}\nWrite a complete, executable Python script to solve this. Return ONLY the python code, no markdown blocks."
        system_prompt = "You are an expert Python developer. Write production-ready, self-contained code."
        
        code = self._call_llm(prompt, system_prompt)
        # Clean markdown markers if LLM included them
        code = code.replace("```python", "").replace("```", "").strip()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        code_file = self.workspace / "ai_agent" / "code" / f"task_{timestamp}.py"
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        self.code_history.append(str(code_file))
        print(f"✅ 代码已保存：{code_file}")
        return str(code_file)

    def execute(self, code_file: str) -> Dict:
        print(f"\n{'='*70}\n▶️ 执行代码\n{'='*70}")
        try:
            result = subprocess.run(['python3', code_file], capture_output=True, text=True, timeout=120, cwd=str(self.workspace))
            output = {'stdout': result.stdout, 'stderr': result.stderr, 'returncode': result.returncode, 'success': result.returncode == 0, 'code_file': code_file}
            print(f"✅ 执行完成 | 返回码：{result.returncode}")
            return output
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def learn(self, result: Dict) -> Dict:
        print(f"\n{'='*70}\n📚 学习反馈 (LLM Real-time)\n{'='*70}")
        prompt = f"Execution result: {result}\nDecide if the task is 'done' or needs 'retry'. Return JSON with 'status' and 'next_action'."
        system_prompt = "You are a QA engineer. Return ONLY pure JSON."
        
        response = self._call_llm(prompt, system_prompt)
        try:
            return json.loads(response)
        except:
            return {"status": "failed", "next_action": "retry"}

    def run(self, task: str) -> Dict:
        print(f"\n{'🚀'*35}\nAI 智能体启动\n任务：{task}\n{'🚀'*35}\n")
        self.task = task
        self.current_iteration = 0
        decision = {"next_action": "start"}
        
        while self.current_iteration < self.max_iterations:
            self.current_iteration += 1
            print(f"\n{'='*70}\n🔄 第 {self.current_iteration} 次迭代\n{'='*70}")
            thought = self.think(task)
            code_file = self.code(task, thought)
            result = self.execute(code_file)
            decision = self.learn(result)
            if decision.get('next_action') == 'done':
                break
            task = f"{task} (Last Error: {result.get('stderr', 'Unknown')})"
            
        return {'task': self.task, 'iterations': self.current_iteration, 'completed': decision.get('next_action') == 'done'}

if __name__ == "__main__":
    agent = AIAgent()
    print(agent.run("Hello World Test"))
