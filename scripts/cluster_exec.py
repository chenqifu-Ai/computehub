#!/usr/bin/env python3
"""
cluster_exec - 跨节点命令执行工具

提供在任意 ComputeHub 节点执行命令的能力。
通过 Gateway API 分发任务到目标节点 Worker。

用法：
    python3 scripts/cluster_exec.py <node_id> <command> [--timeout N]
    
    # 或作为模块导入
    from scripts.cluster_exec import cluster_exec, get_nodes
    result = cluster_exec("wanlida-ubuntu", "hostname")
"""

import json
import urllib.request
import urllib.error
import time
import argparse
from typing import Optional, Dict, Any, List

# ============================================================================
# 配置
# ============================================================================

# Gateway 地址（可通过环境变量覆盖）
import os
GATEWAY_URL = os.environ.get("COMPUTEHUB_GATEWAY", "http://127.0.0.1:8282")

DEFAULT_TIMEOUT = 60
MAX_TIMEOUT = 300
POLL_INTERVAL = 2
POLL_TIMEOUT_BUFFER = 30

# 禁止命令黑名单
BLOCKED_COMMANDS = [
    "rm -rf /",
    "rm -rf /*",
    "mkfs",
    "dd if=/dev/zero",
    "dd if=/dev/urandom",
    ":(){ :|:& };:",
    "chmod -R 777 /",
    "chown -R",
    "> /dev/sda",
    "mv /* /dev/null",
]


# ============================================================================
# 核心函数
# ============================================================================

def cluster_exec(
    node_id: str,
    command: str,
    timeout: int = DEFAULT_TIMEOUT,
    workdir: Optional[str] = None,
    gateway_url: Optional[str] = None
) -> Dict[str, Any]:
    """
    在指定节点执行命令，同步返回结果。
    
    Args:
        node_id: 目标节点 ID（如 ecs-p2ph, wanlida-work01）
        command: 要执行的命令
        timeout: 超时时间（秒），默认 60，最大 300
        workdir: 工作目录，默认 ~
        gateway_url: Gateway 地址，默认使用环境变量或本地
    
    Returns:
        {
            "success": bool,
            "node_id": str,
            "command": str,
            "exit_code": int,
            "stdout": str,
            "stderr": str,
            "duration_ms": int,
            "task_id": str,
            "error": {...}  # 仅失败时
        }
    """
    if not node_id:
        return _error_response("INVALID_PARAMS", "node_id 不能为空")
    if not command:
        return _error_response("INVALID_PARAMS", "command 不能为空")
    
    blocked = _check_blocked_command(command)
    if blocked:
        return _error_response("BLOCKED_COMMAND", f"命令被禁止: {blocked}")
    
    timeout = min(timeout, MAX_TIMEOUT)
    gw = gateway_url or GATEWAY_URL
    
    task_result = _submit_task(gw, node_id, command, timeout, workdir)
    if not task_result.get("success"):
        return task_result
    
    task_id = task_result["task_id"]
    result = _poll_task_result(gw, task_id, timeout)
    result["node_id"] = node_id
    result["command"] = command
    result["task_id"] = task_id
    
    return result


def cluster_exec_async(
    node_id: str,
    command: str,
    timeout: int = DEFAULT_TIMEOUT,
    workdir: Optional[str] = None,
    gateway_url: Optional[str] = None
) -> Dict[str, Any]:
    """异步提交任务，立即返回 task_id"""
    if not node_id or not command:
        return _error_response("INVALID_PARAMS", "node_id 和 command 不能为空")
    
    blocked = _check_blocked_command(command)
    if blocked:
        return _error_response("BLOCKED_COMMAND", f"命令被禁止: {blocked}")
    
    timeout = min(timeout, MAX_TIMEOUT)
    gw = gateway_url or GATEWAY_URL
    
    return _submit_task(gw, node_id, command, timeout, workdir)


def wait_for_task(
    task_id: str,
    timeout: int = DEFAULT_TIMEOUT,
    gateway_url: Optional[str] = None
) -> Dict[str, Any]:
    """等待任务完成，返回结果"""
    gw = gateway_url or GATEWAY_URL
    return _poll_task_result(gw, task_id, timeout)


def get_nodes(gateway_url: Optional[str] = None) -> Dict[str, Any]:
    """
    获取集群所有节点状态。
    
    Returns:
        {
            "success": true,
            "nodes": [{"node_id": "xxx", "status": "online", ...}, ...],
            "count": 4
        }
    """
    gw = gateway_url or GATEWAY_URL
    
    try:
        url = f"{gw}/api/v1/nodes/list"
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read().decode())
        
        nodes = data.get("data", [])
        return {
            "success": True,
            "nodes": nodes,
            "count": len(nodes)
        }
    except Exception as e:
        return {
            "success": False,
            "error": {"code": "API_ERROR", "message": str(e)}
        }


def get_task_status(
    task_id: str,
    node_id: str,
    gateway_url: Optional[str] = None
) -> Dict[str, Any]:
    """查询任务状态"""
    gw = gateway_url or GATEWAY_URL
    
    try:
        url = f"{gw}/api/v1/tasks/detail?task_id={task_id}&node_id={node_id}"
        resp = urllib.request.urlopen(url, timeout=10)
        data = json.loads(resp.read().decode())
        
        task = data.get("data", {})
        return {
            "success": True,
            "task": task,
            "status": task.get("status", "unknown")
        }
    except Exception as e:
        return {
            "success": False,
            "error": {"code": "API_ERROR", "message": str(e)}
        }


# ============================================================================
# 内部函数
# ============================================================================

def _submit_task(
    gateway_url: str,
    node_id: str,
    command: str,
    timeout: int,
    workdir: Optional[str]
) -> Dict[str, Any]:
    """提交任务到 Gateway"""
    
    payload = {
        "node_id": node_id,
        "command": command,
        "timeout": timeout
    }
    if workdir:
        payload["workdir"] = workdir
    
    try:
        url = f"{gateway_url}/api/v1/tasks/submit"
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )
        
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read().decode())
        
        if result.get("success") or result.get("data", {}).get("task_id"):
            return {
                "success": True,
                "task_id": result.get("data", {}).get("task_id"),
                "node_id": node_id
            }
        else:
            return _error_response(
                "SUBMIT_FAILED",
                result.get("error", "提交任务失败")
            )
    
    except urllib.error.HTTPError as e:
        return _error_response(
            "HTTP_ERROR",
            f"HTTP {e.code}: {e.read().decode()[:200]}"
        )
    except urllib.error.URLError as e:
        return _error_response(
            "CONNECTION_ERROR",
            f"无法连接 Gateway: {e.reason}"
        )
    except Exception as e:
        return _error_response("UNKNOWN_ERROR", str(e))


def _poll_task_result(
    gateway_url: str,
    task_id: str,
    timeout: int
) -> Dict[str, Any]:
    """轮询任务直到完成或超时"""
    
    start_time = time.time()
    max_wait = timeout + POLL_TIMEOUT_BUFFER
    
    while time.time() - start_time < max_wait:
        try:
            url = f"{gateway_url}/api/v1/tasks/detail?task_id={task_id}"
            resp = urllib.request.urlopen(url, timeout=10)
            data = json.loads(resp.read().decode())
            
            task = data.get("data", {})
            status = task.get("status", "unknown")
            
            if status in ("completed", "success", "failed", "error"):
                duration_ms = int((time.time() - start_time) * 1000)
                
                return {
                    "success": status in ("completed", "success"),
                    "exit_code": task.get("exit_code", -1),
                    "stdout": task.get("stdout", ""),
                    "stderr": task.get("stderr", ""),
                    "status": status,
                    "duration_ms": duration_ms
                }
            
            time.sleep(POLL_INTERVAL)
        
        except urllib.error.URLError:
            time.sleep(POLL_INTERVAL)
            continue
        except Exception as e:
            return _error_response("POLL_ERROR", str(e))
    
    return _error_response("TIMEOUT", f"任务 {task_id} 执行超时（>{timeout}s）")


def _check_blocked_command(command: str) -> Optional[str]:
    """检查命令是否在黑名单中"""
    cmd_lower = command.lower()
    for blocked in BLOCKED_COMMANDS:
        if blocked.lower() in cmd_lower:
            return blocked
    return None


def _error_response(code: str, message: str) -> Dict[str, Any]:
    """生成错误响应"""
    return {
        "success": False,
        "exit_code": -1,
        "stdout": "",
        "stderr": message,
        "error": {
            "code": code,
            "message": message
        }
    }


# ============================================================================
# 便捷类（兼容 OPC plugin）
# ============================================================================

class OPC:
    """OPC 便捷类"""
    
    def __init__(self, gateway_url: str = None):
        self.gateway_url = gateway_url or GATEWAY_URL
    
    def run(
        self,
        command: str,
        node: str = None,
        timeout: int = DEFAULT_TIMEOUT,
        wait: bool = True
    ) -> Dict[str, Any]:
        """执行命令"""
        if not node:
            nodes = get_nodes(self.gateway_url)
            if not nodes.get("success") or not nodes.get("nodes"):
                return _error_response("NO_NODES", "没有可用节点")
            # 找第一个在线节点
            for n in nodes["nodes"]:
                if n.get("status") == "online":
                    node = n["node_id"]
                    break
            if not node:
                node = nodes["nodes"][0]["node_id"]
        
        if wait:
            return cluster_exec(node, command, timeout, gateway_url=self.gateway_url)
        else:
            return cluster_exec_async(node, command, timeout, gateway_url=self.gateway_url)
    
    def run_all(self, command: str, timeout: int = DEFAULT_TIMEOUT) -> List[Dict[str, Any]]:
        """广播到所有节点"""
        nodes = get_nodes(self.gateway_url)
        if not nodes.get("success"):
            return []
        
        results = []
        for node_info in nodes["nodes"]:
            node_id = node_info["node_id"]
            result = cluster_exec(node_id, command, timeout, gateway_url=self.gateway_url)
            results.append(result)
        
        return results
    
    def nodes(self) -> List[Dict[str, Any]]:
        """获取节点列表"""
        result = get_nodes(self.gateway_url)
        return result.get("nodes", [])
    
    def summary(self) -> str:
        """集群概况"""
        nodes = self.nodes()
        if not nodes:
            return "集群无节点"
        
        lines = [f"集群概况 ({len(nodes)} 节点)"]
        for n in nodes:
            status = n.get("status", "unknown")
            version = n.get("version", "?")
            node_id = n.get("node_id", "?")
            emoji = "🟢" if status == "online" else "🔴"
            lines.append(f"  {emoji} {node_id} v{version} ({status})")
        
        return "\n".join(lines)


# 全局实例
opc = OPC()


# ============================================================================
# CLI 入口
# ============================================================================

def main():
    parser = argparse.ArgumentParser(
        description="跨节点命令执行工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  # 在指定节点执行命令
  python3 scripts/cluster_exec.py wanlida-ubuntu "hostname"
  
  # 查看所有节点
  python3 scripts/cluster_exec.py --list-nodes
  
  # 集群概况
  python3 scripts/cluster_exec.py --summary
        """
    )
    
    parser.add_argument("node_id", nargs="?", help="目标节点 ID")
    parser.add_argument("command", nargs="?", help="要执行的命令")
    parser.add_argument("--timeout", "-t", type=int, default=60, help="超时时间（秒）")
    parser.add_argument("--gateway", "-g", help="Gateway 地址")
    parser.add_argument("--list-nodes", "-l", action="store_true", help="列出所有节点")
    parser.add_argument("--summary", "-s", action="store_true", help="显示集群概况")
    
    args = parser.parse_args()
    
    # 显示集群概况
    if args.summary:
        print(opc.summary())
        return
    
    # 列出节点
    if args.list_nodes:
        nodes = get_nodes(args.gateway)
        if nodes.get("success"):
            print(f"在线节点: {nodes['count']}")
            for n in nodes["nodes"]:
                status = "🟢" if n.get("status") == "online" else "🔴"
                print(f"  {status} {n['node_id']} v{n.get('version', '?')}")
        else:
            print(f"获取节点失败: {nodes.get('error')}")
        return
    
    # 执行命令
    if not args.node_id or not args.command:
        parser.error("需要指定 node_id 和 command，或使用 --list-nodes / --summary")
    
    result = cluster_exec(args.node_id, args.command, args.timeout, gateway_url=args.gateway)
    
    if result.get("success"):
        print(f"✅ 成功 (耗时 {result.get('duration_ms', 0)}ms)")
        print(f"节点: {result['node_id']}")
        print(f"退出码: {result['exit_code']}")
        if result.get("stdout"):
            print(f"输出:\n{result['stdout']}")
        if result.get("stderr"):
            print(f"错误:\n{result['stderr']}")
    else:
        print(f"❌ 失败")
        error = result.get("error", {})
        print(f"错误: [{error.get('code')}] {error.get('message')}")
        if result.get("stderr"):
            print(f"详情: {result['stderr']}")


if __name__ == "__main__":
    main()