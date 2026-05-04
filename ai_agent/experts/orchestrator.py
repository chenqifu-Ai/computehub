#!/usr/bin/env python3
"""
专家协作系统 - Orchestrator
===========================
自动路由请求到对应专家，收集结果后汇总输出。

使用:
    from ai_agent.experts.orchestrator import ExpertOrchestrator
    
    expert_system = ExpertOrchestrator()
    result = expert_system.execute("帮我分析一下这个股票")
    print(result)
"""

import json
import os
import time
import urllib.request
from enum import Enum
from dataclasses import dataclass, field


class ExpertRole(Enum):
    CEO顾问 = "ceo-advisor"
    人力资源 = "hr-expert"
    法律顾问 = "legal-advisor"
    营销专家 = "marketing-expert"
    财务专家 = "finance-expert"
    财务顾问 = "finance-advisor"
    网络专家 = "network-expert"


# 请求分类规则
ROUTING_RULES = {
    "战略": ExpertRole.CEO顾问,
    "商业模式": ExpertRole.CEO顾问,
    "竞争分析": ExpertRole.CEO顾问,
    "招聘": ExpertRole.人力资源,
    "薪酬": ExpertRole.人力资源,
    "绩效": ExpertRole.人力资源,
    "劳动": ExpertRole.人力资源,
    "合同": ExpertRole.法律顾问,
    "公司法": ExpertRole.法律顾问,
    "合规": ExpertRole.法律顾问,
    "品牌": ExpertRole.营销专家,
    "推广": ExpertRole.营销专家,
    "社媒": ExpertRole.营销专家,
    "营销": ExpertRole.营销专家,
    "税务": ExpertRole.财务专家,
    "成本": ExpertRole.财务专家,
    "投资": ExpertRole.财务专家,
    "股票": ExpertRole.财务专家,
    "资金": ExpertRole.财务专家,
    "理财": ExpertRole.财务顾问,
    "保险": ExpertRole.财务顾问,
    "银行": ExpertRole.财务顾问,
    "基金": ExpertRole.财务顾问,
    "网络": ExpertRole.网络专家,
    "安全": ExpertRole.网络专家,
    "云服务": ExpertRole.网络专家,
}


@dataclass
class ExpertResult:
    专家: str
    角色: str
    分析: str
    耗时: float = 0.0


class ExpertOrchestrator:
    """专家协作系统编排器"""
    
    def __init__(self, api_url="http://10.111.223.227:8765/v1/chat/completions"):
        self.workspace = "/root/.openclaw/workspace"
        self.skills_dir = f"{self.workspace}/skills"
        self.api_url = api_url
        self.api_key = "sk-78sadn09bjawde123e"
        
    def route_request(self, user_request: str) -> ExpertRole:
        """根据请求内容路由到对应专家"""
        for keyword, role in ROUTING_RULES.items():
            if keyword in user_request:
                return role
        return ExpertRole.CEO顾问
    
    def _get_role_name(self, role: ExpertRole) -> str:
        names = {
            ExpertRole.CEO顾问: "企业战略顾问",
            ExpertRole.人力资源: "人力资源专家",
            ExpertRole.法律顾问: "法律顾问",
            ExpertRole.营销专家: "营销专家",
            ExpertRole.财务专家: "财务专家",
            ExpertRole.财务顾问: "金融顾问",
            ExpertRole.网络专家: "网络专家",
        }
        return names.get(role, "AI助手")
    
    def load_knowledge(self, expert_role: ExpertRole, max_files=2, max_chars=3000) -> str:
        """加载专家知识库（精简版）"""
        ref_dir = f"{self.skills_dir}/{expert_role.value}/references"
        if not os.path.exists(ref_dir):
            return ""
        
        files = [f for f in os.listdir(ref_dir) if f.endswith('.md')]
        context_parts = []
        for fname in files[:max_files]:
            try:
                fpath = os.path.join(ref_dir, fname)
                with open(fpath, 'r', encoding='utf-8') as f:
                    content = f.read()[:max_chars]
                    context_parts.append(f"【{fname}】{content}")
            except:
                pass
        
        return "\n\n".join(context_parts)[:6000]  # 最多 6000 字符
    
    def ask_expert(self, expert_role: ExpertRole, question: str) -> ExpertResult:
        """向专家提问"""
        start = time.time()
        role_name = self._get_role_name(expert_role)
        
        # 加载知识库
        knowledge = self.load_knowledge(expert_role)
        
        # 构建精简提示
        prompt = f"""你是{role_name}。

{knowledge}

## 用户问题
{question}

请专业、简洁地回答。给出具体建议，标明风险点。"""
        
        # 调用 API
        try:
            payload = json.dumps({
                "model": "qwen3.6-35b",
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": 2000,
                "temperature": 0.7
            }).encode('utf-8')
            
            req = urllib.request.Request(
                self.api_url,
                data=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {self.api_key}"
                }
            )
            
            with urllib.request.urlopen(req, timeout=120) as resp:
                data = json.loads(resp.read())
                msg = data.get("choices", [{}])[0].get("message", {})
                reasoning = msg.get("reasoning", "") or ""
                content = msg.get("content", "") or ""
                result_text = reasoning if reasoning else content
                if not result_text:
                    result_text = "⚠️ 模型返回为空"
                
        except Exception as e:
            result_text = f"⚠️ 请求失败: {str(e)}"
        
        result = ExpertResult(
            专家=expert_role.value,
            角色=role_name,
            分析=result_text,
            耗时=time.time() - start
        )
        return result
    
    def execute(self, user_request: str) -> str:
        """执行专家协作"""
        expert_role = self.route_request(user_request)
        result = self.ask_expert(expert_role, user_request)
        
        return f"""## 🤖 {result.角色} 分析报告

**专家**: {result.专家}
**耗时**: {result.耗时:.2f}s

---

{result.分析}

---

*由 OpenClaw 专家协作系统生成*
"""


if __name__ == "__main__":
    system = ExpertOrchestrator()
    
    tests = [
        "帮我分析一下华联股份这支股票",
        "劳动合同续签需要注意什么法律问题",
        "如何做新媒体营销推广",
    ]
    
    for q in tests:
        print(f"\n{'='*60}")
        print(f"👤 你: {q}")
        print("="*60)
        result = system.execute(q)
        print(result)
