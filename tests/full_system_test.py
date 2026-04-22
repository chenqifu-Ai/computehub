import requests
import time
import json
import logging
import subprocess
import os
from datetime import datetime

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ComputeHub-QA")

class ComputeHubTestSuit:
    def __init__(self, gateway_url="http://localhost:8000"):
        self.gateway_url = gateway_url
        self.test_nodes = []
        self.results = {"passed": 0, "failed": 0}

    def log_result(self, name, success, message=""):
        if success:
            self.results["passed"] += 1
            logger.info(f"✅ TEST PASSED: {name}")
        else:
            self.results["failed"] += 1
            logger.error(f"❌ TEST FAILED: {name} | {message}")

    def setup_environment(self):
        """启动系统组件"""
        logger.info("Setting up environment...")
        # 启动网关 (后台)
        subprocess.Popen(["python3", "/root/.openclaw/workspace/ai_agent/code/computehub/api/rest_api.py"])
        time.sleep(3) # 等待启动

    def test_node_lifecycle(self):
        """测试节点：注册 -> 心跳 -> 状态更新"""
        logger.info("Testing Node Lifecycle...")
        node_id = f"test_node_{int(time.time())}"
        
        # 1. 注册
        reg_data = {"node_id": node_id, "hardware_fingerprint": "fp_test", "os": "Linux", "gpu_model": "T4", "memory_total_mb": 16384}
        r = requests.post(f"{self.gateway_url}/api/v1/node/register", json=reg_data)
        if r.status_code != 200:
            self.log_result("Node Registration", False, r.text)
            return False
        
        # 2. 发送心跳
        hb_data = {"node_id": node_id, "status": "ONLINE", "metrics": {"temperature": 40, "utilization": 10, "power_draw": 50, "memory_used": 1024}, "version": "1.0"}
        r = requests.post(f"{self.gateway_url}/api/v1/node/heartbeat", json=hb_data)
        if r.status_code != 200:
            self.log_result("Heartbeat Submission", False, r.text)
            return False
            
        # 3. 验证状态
        r = requests.get(f"{self.gateway_url}/api/v1/nodes/status")
        nodes_dict = r.json().get("nodes", {})
        # nodes_dict is a dict, convert to list of values
        nodes_list = list(nodes_dict.values()) if isinstance(nodes_dict, dict) else nodes_dict
        found = any(n.get('node_id') == node_id and n.get('status') == 'ONLINE' for n in nodes_list)
        self.log_result("Node Status Sync", found, "Node not found or not ONLINE")
        return found

    def test_scheduling_logic(self):
        """测试调度：提交任务 -> 匹配物理节点"""
        logger.info("Testing Scheduling Logic...")
        
        # 先注册一个可用节点
        node_id = "sched_test_node"
        requests.post(f"{self.gateway_url}/api/v1/node/register", json={"node_id": node_id, "hardware_fingerprint": "fp_sched", "os": "Linux"})
        requests.post(f"{self.gateway_url}/api/v1/node/heartbeat", json={"node_id": node_id, "status": "ONLINE", "metrics": {"temperature": 30, "utilization": 5, "power_draw": 40, "memory_used": 512}, "version": "1.0"})

        # 提交任务
        task_data = {"task_name": "QA_Test_Task", "memory_mb": 2048, "duration_sec": 1}
        r = requests.post(f"{self.gateway_url}/api/v1/tasks/submit", json=task_data)
        
        if r.status_code != 200:
            self.log_result("Task Submission", False, r.text)
            return False
            
        res = r.json()
        if res.get("status") == "DEPLOYING" and res.get("matched_node") == node_id:
            self.log_result("L3 Matching Accuracy", True)
            return True
        else:
            self.log_result("L3 Matching Accuracy", False, f"Expected {node_id}, got {res.get('matched_node')}")
            return False

    def run_all(self):
        self.setup_environment()
        self.test_node_lifecycle()
        self.test_scheduling_logic()
        
        logger.info("========================================")
        logger.info(f"FINAL TEST REPORT: Passed: {self.results['passed']}, Failed: {self.results['failed']}")
        logger.info("========================================")

if __name__ == "__main__":
    tester = ComputeHubTestSuit()
    tester.run_all()
