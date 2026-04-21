import time
import json
import logging
import random
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-Executor")

class TaskExecutor:
    """
    ComputeHub 任务执行器：在物理节点上执行实际算力任务
    """
    def __init__(self, node_id):
        self.node_id = node_id
        self.current_task = None
        self.is_executing = False

    def execute(self, task_id, task_details):
        """
        模拟物理执行过程
        """
        self.current_task = task_id
        self.is_executing = True
        
        duration = task_details.get("duration_sec", 10)
        memory_req = task_details.get("memory_mb", 1024)
        
        logger.info(f"[*] Executing Task {task_id} | Req Memory: {memory_req}MB | Duration: {duration}s")
        
        try:
            # 模拟物理执行过程中的指标波动
            for i in range(duration):
                # 模拟 GPU 负载增加
                load = 30 + random.randint(0, 60) 
                temp = 45 + random.randint(0, 20)
                logger.info(f"[Task {task_id}] Progress: {int((i+1)/duration*100)}% | GPU Load: {load}% | Temp: {temp}C")
                time.sleep(1)
            
            logger.info(f"[+] Task {task_id} execution finished successfully.")
            return {
                "status": "SUCCESS",
                "execution_time": duration,
                "physical_snapshot": {
                    "avg_temp": 55,
                    "avg_util": 65,
                    "peak_memory": memory_req + 100
                },
                "result_hash": "sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
            }
        except Exception as e:
            logger.error(f"[-] Task {task_id} failed: {e}")
            return {"status": "FAILED", "error": str(e)}
        finally:
            self.is_executing = False
            self.current_task = None

if __name__ == "__main__":
    # 模拟独立运行
    executor = TaskExecutor(node_id="node_test_01")
    result = executor.execute("task_123", {"duration_sec": 5, "memory_mb": 4096})
    print(f"Execution Result: {json.dumps(result, indent=2)}")
