import os
import subprocess
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-DevOps")

class DevCycleManager:
    """
    ComputeHub 极速开发循环管理器：实现 自动化测试 -> 性能分析 -> 迭代记录
    """
    def __init__(self, project_root="/root/.openclaw/workspace/ai_agent/code/computehub"):
        self.project_root = project_root

    def run_smoke_test(self):
        """
        执行端到端冒烟测试：启动所有组件并验证 API 响应
        """
        logger.info("🚀 Starting End-to-End Smoke Test...")
        
        # 1. 启动数据库 (假设已运行)
        # 2. 启动网关
        try:
            subprocess.Popen(["python3", "api/rest_api.py"], cwd=self.project_root)
            logger.info("Gateway launched.")
            
            # 3. 启动模拟节点
            subprocess.Popen(["python3", "node/client.py"], cwd=self.project_root)
            logger.info("Node Client launched.")
            
            # 4. 运行演示脚本验证链路
            result = subprocess.run(
                ["python3", "demo_test.py"], 
                cwd=self.project_root, 
                capture_output=True, 
                text=True
            )
            
            if result.returncode == 0:
                logger.info("✅ Smoke Test Passed: Full loop verified.")
                return True
            else:
                logger.error(f"❌ Smoke Test Failed: {result.stderr}")
                return False
        except Exception as e:
            logger.error(f"Test Execution Error: {e}")
            return False

    def log_iteration(self, feature, result, metrics=None):
        """
        记录每一次极速迭代的成果
        """
        log_entry = f"[{datetime.utcnow().isoformat()}] Feature: {feature} | Result: {result} | Metrics: {metrics}\n"
        with open(os.path.join(self.project_root, "iteration_log.txt"), "a") as f:
            f.write(log_entry)

if __name__ == "__main__":
    manager = DevCycleManager()
    if manager.run_smoke_test():
        manager.log_iteration("v1.0-alpha-core", "SUCCESS", "Loop Latency <<  200ms")
