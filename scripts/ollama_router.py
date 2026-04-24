# Ollama Router Python Client
# 自动切换API端点的Python客户端

import requests
import time
import logging
from typing import Optional, List, Dict, Any
from dataclasses import dataclass

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class OllamaServer:
    """Ollama服务器配置"""
    name: str
    host: str
    port: int = 11434
    priority: int = 0  # 优先级，数字越小优先级越高
    api_key: str = ""  # API Key（可选）
    
    @property
    def url(self) -> str:
        if self.port == 443:
            return f"https://{self.host}"
        return f"http://{self.host}:{self.port}"
    
    def __str__(self):
        auth = " (API Key)" if self.api_key else ""
        return f"{self.name}({self.host}:{self.port}{auth})"


class OllamaRouter:
    """Ollama路由器 - 自动故障转移"""
    
    def __init__(self, servers: List[OllamaServer], timeout: int = 5):
        self.servers = sorted(servers, key=lambda s: s.priority)
        self.timeout = timeout
        self.current_server: Optional[OllamaServer] = None
        self.failed_servers: set = set()
        
    def check_server(self, server: OllamaServer) -> bool:
        """检查服务器是否可用"""
        try:
            headers = {}
            if server.api_key:
                headers["Authorization"] = f"Bearer {server.api_key}"
            
            response = requests.get(
                f"{server.url}/api/tags",
                headers=headers,
                timeout=self.timeout
            )
            return response.status_code == 200
        except Exception as e:
            logger.debug(f"服务器 {server} 检查失败: {e}")
            return False
    
    def get_available_server(self) -> Optional[OllamaServer]:
        """获取可用的服务器"""
        for server in self.servers:
            if server in self.failed_servers:
                continue
                
            if self.check_server(server):
                if self.current_server != server:
                    if self.current_server:
                        logger.warning(f"🔄 切换到服务器: {server}")
                    else:
                        logger.info(f"✅ 使用服务器: {server}")
                    self.current_server = server
                    self.failed_servers.discard(server)  # 从失败列表移除
                return server
            else:
                self.failed_servers.add(server)
                logger.error(f"❌ 服务器不可用: {server}")
        
        # 所有服务器都失败，重置失败列表重试
        if self.failed_servers:
            logger.warning("⚠️ 所有服务器都失败，重置重试...")
            self.failed_servers.clear()
            return self.get_available_server()
        
        return None
    
    def request(self, method: str, endpoint: str, **kwargs) -> Optional[requests.Response]:
        """发送请求，自动处理故障转移"""
        server = self.get_available_server()
        if not server:
            logger.error("❌ 没有可用的服务器")
            return None
        
        url = f"{server.url}{endpoint}"
        
        # 添加认证头
        headers = kwargs.pop('headers', {})
        if server.api_key:
            headers["Authorization"] = f"Bearer {server.api_key}"
        kwargs['headers'] = headers
        
        try:
            response = requests.request(
                method=method,
                url=url,
                timeout=self.timeout,
                **kwargs
            )
            return response
        except Exception as e:
            logger.error(f"请求失败: {e}")
            self.failed_servers.add(server)
            self.current_server = None
            # 递归重试
            return self.request(method, endpoint, **kwargs)
    
    def generate(self, model: str, prompt: str, **kwargs) -> Optional[Dict[str, Any]]:
        """生成文本"""
        data = {
            "model": model,
            "prompt": prompt,
            "stream": False,
            **kwargs
        }
        
        response = self.request("POST", "/api/generate", json=data)
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def chat(self, model: str, messages: List[Dict], **kwargs) -> Optional[Dict[str, Any]]:
        """聊天"""
        data = {
            "model": model,
            "messages": messages,
            "stream": False,
            **kwargs
        }
        
        response = self.request("POST", "/api/chat", json=data)
        if response and response.status_code == 200:
            return response.json()
        return None
    
    def list_models(self) -> List[str]:
        """获取模型列表"""
        response = self.request("GET", "/api/tags")
        if response and response.status_code == 200:
            data = response.json()
            return [m['name'] for m in data.get('models', [])]
        return []
    
    def embeddings(self, model: str, prompt: str) -> Optional[List[float]]:
        """获取嵌入向量"""
        data = {
            "model": model,
            "prompt": prompt
        }
        
        response = self.request("POST", "/api/embeddings", json=data)
        if response and response.status_code == 200:
            return response.json().get('embedding')
        return None


# 使用示例
if __name__ == "__main__":
    # 配置服务器列表
    servers = [
        OllamaServer(name="主服务器", host="192.168.1.7", port=11434, priority=1),
        OllamaServer(name="ollama.com", host="ollama.com", port=443, priority=2, api_key="8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii"),
        # 可以添加更多备用服务器
    ]
    
    # 创建路由器
    router = OllamaRouter(servers)
    
    print("🧪 测试 Ollama Router")
    print("=" * 50)
    
    # 测试获取模型列表
    print("\n1. 获取可用模型:")
    models = router.list_models()
    for model in models:
        print(f"  - {model}")
    
    # 测试生成
    if models:
        print(f"\n2. 测试生成 (使用 {models[0]}):")
        result = router.generate(
            model=models[0],
            prompt="用一句话介绍自己",
            options={"temperature": 0.7}
        )
        if result:
            print(f"   响应: {result.get('response', '无响应')}")
        else:
            print("   ❌ 生成失败")
    
    # 测试聊天
    print(f"\n3. 测试聊天:")
    chat_result = router.chat(
        model=models[0] if models else "llama3",
        messages=[
            {"role": "system", "content": "你是一个友好的助手"},
            {"role": "user", "content": "你好"}
        ]
    )
    if chat_result:
        print(f"   响应: {chat_result.get('message', {}).get('content', '无响应')}")
    else:
        print("   ❌ 聊天失败")
    
    print("\n✅ 测试完成")