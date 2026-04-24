#!/usr/bin/env python3
import subprocess
import os
from datetime import datetime

scripts = [
    "financial_advisor_stock_analysis.py",
    "finance_expert_analysis.py",
    "legal_advisor_risk_check.py", 
    "network_expert_system_check.py"
]

print(f"👨‍💼 专家工作编排器启动 - {datetime.now().strftime('%H:%M:%S')}")

for script in scripts:
    script_path = f"/root/.openclaw/workspace/ai_agent/code/expert_scripts/{script}"
    if os.path.exists(script_path):
        result = subprocess.run(["python3", script_path], capture_output=True, text=True)
        if result.returncode == 0:
            print(f"✅ {script}: 执行成功")
        else:
            print(f"❌ {script}: 执行失败")

print("🎯 专家工作编排完成")
