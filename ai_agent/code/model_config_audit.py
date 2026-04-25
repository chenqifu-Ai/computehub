#!/usr/bin/env python3
"""
模型配置全面审计脚本
- 检查所有已知的模型配置
- 测试每个配置的连通性
- 生成可用/不可用报告
- 提供清理建议
"""

import os
import sys
import json
import time
import subprocess
from typing import Dict, List, Tuple

class ModelConfigAuditor:
    def __init__(self):
        self.configs_to_test = {
            # 从 MEMORY.md 和 HEARTBEAT.md 中提取的配置
            "qwen3.6-35b-local": {
                "url": "http://58.23.129.98:8000/v1",
                "type": "local_api",
                "expected_models": ["qwen3.6-35b"]
            },
            "qwen3.6-35b-alt": {
                "url": "http://58.23.129.98:8001/v1", 
                "type": "local_api",
                "expected_models": ["qwen3.6-35b"]
            },
            "ollama-cloud": {
                "url": "https://ollama.com/api",
                "type": "cloud_api",
                "api_key_env": "OLLAMA_API_KEY"
            },
            "ollama-cloud-2": {
                "url": "https://ollama.com/api/generate",
                "type": "cloud_api",
                "api_key_env": "OLLAMA_API_KEY"
            },
            "modelstudio": {
                "url": "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation",
                "type": "cloud_api",
                "api_key_env": "DASHSCOPE_API_KEY"
            },
            "zhangtuo-ai": {
                "url": "https://ai.zhangtuokeji.top:9090/v1",
                "type": "cloud_api",
                "api_key_env": "ZHANGTUO_API_KEY"
            },
            "local-ollama": {
                "url": "http://localhost:11434/api/tags",
                "type": "local_ollama"
            },
            "remote-ollama": {
                "url": "http://192.168.1.7:11434/api/tags",
                "type": "remote_ollama"
            }
        }
        self.results = {}
        
    def test_http_endpoint(self, url: str, timeout: int = 10) -> Tuple[bool, str]:
        """测试HTTP端点连通性"""
        try:
            cmd = ["curl", "-s", "-f", f"-m {timeout}", url]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return True, "Connected successfully"
            else:
                return False, f"Connection failed (code: {result.returncode})"
        except Exception as e:
            return False, f"Exception: {str(e)}"
    
    def test_ollama_local(self) -> Tuple[bool, str, List[str]]:
        """测试本地Ollama服务"""
        try:
            cmd = ["curl", "-s", "-f", "-m 5", "http://localhost:11434/api/tags"]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                try:
                    data = json.loads(result.stdout)
                    models = [model.get("name", "") for model in data.get("models", [])]
                    return True, f"Found {len(models)} models", models
                except:
                    return True, "Connected but JSON parse failed", []
            else:
                return False, f"Connection failed (code: {result.returncode})", []
        except Exception as e:
            return False, f"Exception: {str(e)}", []
    
    def audit_all_configs(self):
        """审计所有配置"""
        print("🔍 开始全面模型配置审计...")
        print("=" * 60)
        
        for config_name, config in self.configs_to_test.items():
            print(f"\n🧪 测试配置: {config_name}")
            print(f"   URL: {config['url']}")
            
            if config["type"] in ["local_ollama", "remote_ollama"]:
                if "localhost" in config["url"]:
                    success, message, models = self.test_ollama_local()
                    self.results[config_name] = {
                        "success": success,
                        "message": message,
                        "models": models,
                        "type": config["type"]
                    }
                else:
                    # 测试远程Ollama
                    success, message = self.test_http_endpoint(config["url"])
                    self.results[config_name] = {
                        "success": success,
                        "message": message,
                        "type": config["type"]
                    }
            else:
                success, message = self.test_http_endpoint(config["url"])
                self.results[config_name] = {
                    "success": success,
                    "message": message,
                    "type": config["type"]
                }
            
            status = "✅ 可用" if success else "❌ 不可用"
            print(f"   状态: {status} - {message}")
            time.sleep(1)  # 避免请求过快
        
        print("\n" + "=" * 60)
        self.generate_report()
    
    def generate_report(self):
        """生成审计报告"""
        available = []
        unavailable = []
        
        for name, result in self.results.items():
            if result["success"]:
                available.append(name)
            else:
                unavailable.append(name)
        
        print(f"\n📊 审计结果摘要:")
        print(f"✅ 可用配置 ({len(available)}): {', '.join(available) if available else '无'}")
        print(f"❌ 不可用配置 ({len(unavailable)}): {', '.join(unavailable) if unavailable else '无'}")
        
        # 保存详细报告
        report_data = {
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "available_configs": available,
            "unavailable_configs": unavailable,
            "detailed_results": self.results
        }
        
        with open("/root/.openclaw/workspace/ai_agent/results/model_audit_report.json", "w") as f:
            json.dump(report_data, f, indent=2, ensure_ascii=False)
        
        print(f"\n📋 详细报告已保存到: /root/.openclaw/workspace/ai_agent/results/model_audit_report.json")
        
        # 生成清理建议
        if unavailable:
            print(f"\n🧹 清理建议:")
            print("以下配置应从配置文件中移除或注释掉:")
            for config in unavailable:
                print(f"  - {config}")

if __name__ == "__main__":
    auditor = ModelConfigAuditor()
    auditor.audit_all_configs()