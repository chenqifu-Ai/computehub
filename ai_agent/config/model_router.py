#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多模型路由系统
根据场景自动选择最佳模型
"""
import os
import time
import logging
from enum import Enum
from typing import Optional, Dict, Any
from dataclasses import dataclass

# 导入适配层
import sys
sys.path.insert(0, str(__import__('pathlib').Path(__file__).parent.parent))
from ai_agent.config.qwen36_adapter import Qwen36Adapter, Qwen36Config, AdapterError

logger = logging.getLogger("model_router")

class ModelType(Enum):
    """模型类型"""
    QWEN36_STANDARD = "qwen3.6-35b"  # 标准版 - 代码生成/复杂推理
    QWEN36_COMMON = "qwen3.6-35b-common"  # 通用版 - 快速问答/简单任务
    DEEPSEEK = "deepseek-v3.1:671b"  # 深度推理
    OLLAMA_LOCAL = "ollama/qwen3.6-35b"  # 本地 Ollama

@dataclass
class ModelEndpoint:
    """模型端点配置"""
    name: str
    url: str
    api_key: str
    model: str
    timeout: int = 120
    max_tokens: int = 4096
    description: str = ""

class ModelRouter:
    """模型路由器"""
    
    def __init__(self):
        self.adapters = {}
        self.stats = {
            "total_calls": 0,
            "model_usage": {},
            "success_rate": {},
            "avg_latency": {},
        }
        self._setup_endpoints()
    
    def _setup_endpoints(self):
        """设置模型端点"""
        # qwen3.6-35b 通用版 (快速)
        config_common = Qwen36Config(
            api_key=os.getenv("QWEN36_API_KEY_COMMON", os.getenv("QWEN36_API_KEY", "")),
            model="qwen3.6-35b-common",
            url=os.getenv("QWEN36_API_URL_COMMON", "https://ai.zhangtuokeji.top:9090/v1/chat/completions"),
            timeout=30,  # 快速响应
            max_tokens=2048,
        )
        self.adapters["common"] = Qwen36Adapter(config=config_common)
        self.stats["model_usage"]["common"] = 0
        self.stats["success_rate"]["common"] = 100.0
        self.stats["avg_latency"]["common"] = 0.0
        
        # qwen3.6-35b 标准版 (深度推理)
        config_std = Qwen36Config(
            api_key=os.getenv("QWEN36_API_KEY_STD", os.getenv("QWEN36_API_KEY", "")),
            model="qwen3.6-35b",
            url=os.getenv("QWEN36_API_URL_STD", "https://ai.zhangtuokeji.top:9090/v1/chat/completions"),
            timeout=60,
            max_tokens=4096,
        )
        self.adapters["standard"] = Qwen36Adapter(config=config_std)
        self.stats["model_usage"]["standard"] = 0
        self.stats["success_rate"]["standard"] = 100.0
        self.stats["avg_latency"]["standard"] = 0.0
    
    def get_best_model(self, task_type: str) -> str:
        """根据任务类型选择最佳模型"""
        task_type = task_type.lower()
        
        # 快速问答/简单任务 → 通用版
        if any(keyword in task_type for keyword in ["问答", "聊天", "简单", "快速", "常识", "翻译", "总结"]):
            return "common"
        
        # 代码生成/复杂推理 → 标准版
        if any(keyword in task_type for keyword in ["代码", "推理", "复杂", "逻辑", "数学", "调试"]):
            return "standard"
        
        # 默认使用通用版 (更快)
        return "common"
    
    def ask(self, prompt: str, task_type: str = "general", system: str = None) -> str:
        """
        根据任务类型自动选择模型并提问
        
        Args:
            prompt: 用户问题
            task_type: 任务类型 (用于选择模型)
            system: 系统提示词
        
        Returns:
            模型回答
        """
        # 选择最佳模型
        model_name = self.get_best_model(task_type)
        
        # 记录调用
        self.stats["total_calls"] += 1
        self.stats["model_usage"][model_name] = self.stats["model_usage"].get(model_name, 0) + 1
        
        # 获取适配器
        adapter = self.adapters.get(model_name)
        if not adapter:
            raise AdapterError(f"未找到适配器: {model_name}")
        
        # 调用模型
        start_time = time.time()
        try:
            result = adapter.ask(prompt, system)
            elapsed = time.time() - start_time
            
            # 更新统计
            if model_name not in self.stats["avg_latency"]:
                self.stats["avg_latency"][model_name] = elapsed * 1000
            else:
                # 移动平均
                count = self.stats["model_usage"][model_name]
                self.stats["avg_latency"][model_name] = (
                    self.stats["avg_latency"][model_name] * (count - 1) + elapsed * 1000
                ) / count
            
            return result
        except Exception as e:
            logger.error(f"模型 {model_name} 调用失败: {e}")
            # 尝试降级到另一个模型
            fallback_model = "standard" if model_name == "common" else "common"
            logger.info(f"尝试降级到模型: {fallback_model}")
            
            fallback_adapter = self.adapters.get(fallback_model)
            if fallback_adapter:
                try:
                    return fallback_adapter.ask(prompt, system)
                except Exception as fallback_error:
                    logger.error(f"降级也失败: {fallback_error}")
                    raise
    
    def get_stats(self) -> dict:
        """获取路由统计"""
        return {
            **self.stats,
            "total_models": len(self.adapters),
            "available_models": list(self.adapters.keys()),
        }
    
    def summary(self) -> str:
        """获取路由统计摘要"""
        return (
            f"模型路由统计:\n"
            f"  总调用: {self.stats['total_calls']}\n"
            f"  可用模型: {', '.join(self.adapters.keys())}\n"
            f"  使用分布: {self.stats['model_usage']}"
        )

# 便捷函数
_router = None

def get_router() -> ModelRouter:
    """获取全局路由器实例"""
    global _router
    if _router is None:
        _router = ModelRouter()
    return _router

def ask_with_router(prompt: str, task_type: str = "general", system: str = None) -> str:
    """便捷函数：自动选择模型并提问"""
    return get_router().ask(prompt, task_type, system)
