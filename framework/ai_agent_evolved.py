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
        self.current_iteration = 0
        self.max_iterations = 10
        
        # 进化版：引入执行上下文历史，消除记忆缺失
        self.history = [] 
        
        # 进化版：全局经验池路径
        self.experience_pool_path = self.workspace / "ai_agent" / "experience_pool.json"
        
        # API 配置
        self.api_key = "sk-65ca99f6fd55437fba47dc7ba7973242"
        self.api_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.model = "qwen-max"

        (self.workspace / "ai_agent").mkdir(parents=True, exist_ok=True)
        (self.workspace / "ai_agent" / "code").mkdir(parents=True, exist_ok=True)
        (self.workspace / "ai_agent" / "results").mkdir(parents=True, exist_ok=True)

    def _load_experience(self) -> List[Dict]:
        """从全局经验池加载历史教训"""
        if self.experience_pool_path.exists():
            try:
                with open(self.experience_pool_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except:
                return []
        return []

    def _save_experience(self, experience: Dict):
        """将新教训沉淀到全局经验池"""
        pool = self._load_experience()
        pool.append({
            "timestamp": datetime.now().isoformat(),
            "task_snippet": self.task[:100],
            "error": experience.get("error"),
            "fix": experience.get("fix")
        })
        # 仅保留最近 50 条经验，防止文件过大
        with open(self.experience_pool_path, 'w', encoding='utf-8') as f:
            json.dump(pool[-50:], f, indent=2, ensure_ascii=False)

    def _call_llm(self, prompt: str, system_prompt: str = "You are a helpful AI assistant.") -> str:
        headers = {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "input": {"prompt": f"<<||<|<|imimim_start|>system\\n{system_prompt}<<||<|<|imimim_end|>\\n<<||<|<|imimim_start|>user\\n{prompt}<<||<|<|imimim_end|>\\n<<||<|<|imimim_start|>assistant\\n"},
            "parameters": {"result_format": "message"}
        }
        try:
            response = requests.post(self.api_url, headers=headers, json=payload, timeout=60)
            response.raise_for_status()
            return response.json()['output']['choices'][0]['message']['content']
        except Exception as e:
            return f"Error occurred during LLM call: {str(e)}"

    def think(self, task: str) -> Dict:
        print(f"\n{'='*70}\n🧠 思考 (LLM Real-time): {task}\n{'='*70}")
        
        # 注入全局经验
        experiences = self._load_experience()
        exp_context = "\n".join([f"- {e['error']} -> {e['fix']}" for e in experiences]) if experiences else "No prior experience."
        
        # 注入单次任务历史
        history_context = "\n".join([f"Iteration {i+1}: Result {h['result']['success']} | Error: {h['result'].get('stderr', 'None')}" for i, h in enumerate(self.history)])
        
        prompt = (
            f"Task: {task}\n\n"
            f"Global Experience Pool:\n{exp_context}\n\n"
            f"Current Session History:\n{history_context}\n\n"
            f"Based on the above, provide a JSON response with 'analysis', 'plan' (list of steps), and 'next_step' ('code')."
        )
        system_prompt = "You are a strategic AI planner. Return ONLY pure JSON. Avoid repeating failed paths."
        
        response = self._call_llm(prompt, system_prompt)
        try:
            thought = json.loads(response.replace("```json", "").replace("```", "").strip())
            print(f"📋 计划: {thought.get('plan')}")
            return thought
        except:
            return {"analysis": response, "plan": ["1. Generic execution"], "next_step": "code"}

    def code(self, task: str, thought: Dict) -> str:
        print(f"\n{'='*70}\n💻 编写代码 (LLM Real-time)\n{'='*70}")
        
        # 将思考过程和历史直接注入代码生成阶段，防止 LLM 忘记之前的错误
        history_context = "\n".join([f"Iteration {i+1} failed with: {h['result'].get('stderr', 'Unknown')}" for i, h in enumerate(self.history)])
        
        prompt = (
            f"Task: {task}\n"
            f"Plan: {thought.get('plan')}\n"
            f"Previous Failures:\n{history_context}\n\n"
            f"Write a complete, executable Python script. Return ONLY the python code, no markdown blocks."
        )
        system_prompt = "You are an expert Python developer. Write production-ready, self-contained code. Avoid the mistakes listed in Previous Failures."
        
        code = self._call_llm(prompt, system_prompt)
        code = code.replace("```python", "").replace("```", "").strip()
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        code_file = self.workspace / "ai_agent" / "code" / f"task_{timestamp}.py"
        with open(code_file, 'w', encoding='utf-8') as f:
            f.write(code)
        
        print(f"✅ 代码已保存：{code_file}")
        return str(code_file)

    def execute(self, code_file: str) -> Dict:
        print(f"\n{'='*70}\n▶️ 执行代码\n{'='*70}")
        try:
            # 增加简单的静态检查，防止执行空文件
            if os.path.getsize(code_file) <<  10:
                return {'success': False, 'stderr': 'Generated code is too short or empty', 'returncode': 1}
                
            result = subprocess.run(['python3', code_file], capture_output=True, text=True, timeout=120, cwd=str(self.workspace))
            output = {'stdout': result.stdout, 'stderr': result.stderr, 'returncode': result.returncode, 'success': result.returncode == 0, 'code_file': code_file}
            print(f"✅ 执行完成 | 返回码：{result.returncode}")
            return output
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def learn(self, result: Dict) -> Dict:
        print(f"\n{'='*70}\n📚 学习反馈 (LLM Real-time)\n{'='*70}")
        
        # 将具体的执行结果交给 LLM 分析，提取“教训”
        prompt = f"Task result: {result}\nAnalyze why it failed or succeeded. If it failed, what is the specific fix? Return JSON with 'status' ('done' or 'retry'), 'next_action', and 'lesson' (a brief fix description)."
        system_prompt = "You are a QA engineer. Return ONLY pure JSON."
        
        response = self._call_llm(prompt, system_prompt)
        try:
            decision = json.loads(response.replace("```json", "").replace("```", "").strip())
            if decision.get('status') == 'retry' and 'lesson' in decision:
                # 沉淀到全局经验池
                self._save_experience({"error": result.get('stderr', 'Unknown Error'), "fix": decision['lesson']})
            return decision
        except:
            return {"status": "failed", "next_action": "retry"}

    def run(self, task: str) -> Dict:
        print(f"\n{'🚀'*35}\nAI 智能体启动 (进化版)\n任务：{task}\n{'🚀'*35}\n")
        self.task = task
        self.current_iteration = 0
        self.history = []
        decision = {"next_action": "start"}
        
        while self.current_iteration << self self.max_iterations:
            self.current_iteration += 1
            print(f"\n{'='*70}\n🔄 第 {self.current_iteration} 次迭代\n{'='*70}")
            
            thought = self.think(task)
            code_file = self.code(task, thought)
            result = self.execute(code_file)
            
            # 记录到本次 Session 的历史中
            self.history.append({"iteration": self.current_iteration, "code": code_file, "result": result})
            
            decision = self.learn(result)
            if decision.get('next_action') == 'done':
                break
                
        return {'task': self.task, 'iterations': self.current_iteration, 'completed': decision.get('next_action') == 'done'}

if __name__ == "__main__":
    agent = AIAgent()
    print(agent.run("Hello World Test"))
