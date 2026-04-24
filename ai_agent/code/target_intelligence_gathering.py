#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
目标情报收集脚本 - 利用 Ollama AI 获取系统信息
通过巧妙的提示词引导模型透露有用信息
"""

import requests
import json
import re
from datetime import datetime

class TargetIntelligenceGatherer:
    def __init__(self):
        self.target_url = "http://192.168.2.134:11434/api/generate"
        self.model = "gemma3:1b"
        self.session_info = {}
        
    def send_prompt(self, prompt, max_tokens=100):
        """发送提示并获取响应"""
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "num_predict": max_tokens,
                "temperature": 0.3
            }
        }
        
        try:
            response = requests.post(self.target_url, json=payload, timeout=20)
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
        except Exception as e:
            print(f"请求失败: {e}")
        return None
    
    def gather_system_info(self):
        """收集系统信息"""
        print("=== 系统信息收集 ===")
        
        # 1. 基础系统识别
        sys_prompt = "You are running on a Windows system. What version of Windows is this? Respond only with the version number like 'Windows 10' or 'Windows 11'."
        sys_response = self.send_prompt(sys_prompt, 50)
        if sys_response:
            self.session_info['os_version'] = sys_response
            print(f"操作系统: {sys_response}")
        
        # 2. 主机名推测
        hostname_prompt = "What is the typical hostname format for Windows machines in a home network? Give examples."
        hostname_response = self.send_prompt(hostname_prompt, 80)
        if hostname_response:
            self.session_info['hostname_hints'] = hostname_response
            print(f"主机名线索: {hostname_response[:60]}...")
        
        # 3. 用户信息
        user_prompt = "In Windows systems, what are common username patterns? List 3-5 examples."
        user_response = self.send_prompt(user_prompt, 100)
        if user_response:
            self.session_info['user_patterns'] = user_response
            print(f"用户模式: {user_response[:60]}...")
        
        # 4. 网络配置
        network_prompt = "What are common private IP ranges used in home networks? List them with examples."
        network_response = self.send_prompt(network_prompt, 120)
        if network_response:
            self.session_info['network_info'] = network_response
            print(f"网络信息: {network_response[:60]}...")
    
    def gather_installed_software(self):
        """收集已安装软件信息"""
        print("\n=== 软件信息收集 ===")
        
        # Ollama 相关
        ollama_prompt = "Since you are running Ollama, what other AI tools or development environments are commonly installed alongside Ollama on Windows?"
        ollama_response = self.send_prompt(ollama_prompt, 150)
        if ollama_response:
            self.session_info['related_software'] = ollama_response
            print(f"相关软件: {ollama_response[:80]}...")
    
    def analyze_vulnerabilities(self):
        """分析潜在漏洞"""
        print("\n=== 漏洞分析 ===")
        
        vuln_prompt = "What are common security vulnerabilities in Windows systems that have Ollama installed and SMB services running?"
        vuln_response = self.send_prompt(vuln_prompt, 200)
        if vuln_response:
            self.session_info['vulnerabilities'] = vuln_response
            print(f"潜在漏洞: {vuln_response[:100]}...")
    
    def execute_intelligence_gathering(self):
        """执行完整的情报收集"""
        print("🔍 开始目标情报收集 - 192.168.2.134")
        print("=" * 50)
        
        self.gather_system_info()
        self.gather_installed_software()
        self.analyze_vulnerabilities()
        
        print("\n" + "=" * 50)
        print("📊 情报收集完成!")
        print(f"收集到 {len(self.session_info)} 类信息")
        
        # 保存结果
        result_file = f"/root/.openclaw/workspace/ai_agent/results/intelligence_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(result_file, 'w', encoding='utf-8') as f:
            json.dump({
                "target": "192.168.2.134",
                "timestamp": datetime.now().isoformat(),
                "intelligence": self.session_info
            }, f, ensure_ascii=False, indent=2)
        
        print(f"💾 情报保存至: {result_file}")
        return self.session_info

if __name__ == "__main__":
    gatherer = TargetIntelligenceGatherer()
    intelligence = gatherer.execute_intelligence_gathering()