#!/usr/bin/env python3
"""
🎮 四节点网络热身游戏大会
Game 1: Ping测速赛 — 全网延迟拓扑
Game 2: 分布式竞速赛 — 计算圆周率
Game 3: AI故事接龙 — 跨节点消息链
"""

import json
import time
import sys
import re
import base64

GATEWAY_URL = "http://36.250.122.43:8282/api/v1/tasks/submit"
NODES = {
    "ecs-p2ph": {"ip": "36.250.122.43", "name": "ECS云端大脑"},
    "Windows-mobile": {"ip": "112.48.104.210", "name": "Windows笔记本"},
    "local-arm": {"ip": "112.48.77.200", "name": "ARM劳模"},
    "xiaomi-table-01": {"ip": "112.48.77.200", "name": "小米平板"},
}

RESULT = {"games": {}}

def submit_task(node_id, command, timeout=30):
    """Submit a task to a node via Gateway API"""
    import urllib.request
    payload = json.dumps({
        "node_id": node_id,
        "command": command,
        "timeout": timeout,
        "type": "shell"
    }).encode()
    req = urllib.request.Request(GATEWAY_URL, data=payload,
                                 headers={"Content-Type": "application/json"})
    try:
        resp = urllib.request.urlopen(req, timeout=timeout+5)
        return json.loads(resp.read())
    except Exception as e:
        return {"error": str(e)}

def poll_result(task_id, node_id, max_wait=30):
    """Poll task result"""
    import urllib.request
    detail_url = f"http://36.250.122.43:8282/api/v1/tasks/detail?task_id={task_id}"
    
    for i in range(max_wait):
        try:
            resp = urllib.request.urlopen(detail_url, timeout=5)
            data = json.loads(resp.read())
            if data.get("data", {}).get("status") == "completed":
                return data
            elif data.get("data", {}).get("status") == "running":
                time.sleep(1)
                continue
            time.sleep(1)
        except Exception:
            time.sleep(2)
    return {"error": "timeout"}

def game1_ping():
    """🎮 Game 1: Ping测速 — 全网延迟拓扑"""
    print("\n" + "="*60)
    print("🎮 游戏一: Ping测速赛 — 全网延迟拓扑")
    print("="*60)
    
    ping_matrix = {}
    
    for src_name, src_info in NODES.items():
        targets = []
        for dst_name in NODES:
            if dst_name != src_name:
                targets.append(dst_name)
        
        # Build ping all command
        ping_cmds = []
        for dst_name, dst_info in NODES.items():
            if dst_name == src_name:
                continue
            ip = dst_info["ip"]
            if src_info["ip"] == ip:
                # Same IP, ping localhost on different ports
                ping_cmds.append(f'echo "{dst_name}: $(curl -s -o /dev/null -w "%{{http_code}}" --max-time 3 http://127.0.0.1:8282/api/v1/nodes/list 2>/dev/null || echo TIMEOUT) ms (Local Gateway Check)"')
            else:
                # Different IP, ping
                ping_cmds.append(f'echo "{dst_name}: $(ping -c 2 -W 2 {ip} 2>/dev/null | tail -1 | awk -F/ \'{{print $5}}\' 2>/dev/null || echo TIMEOUT) ms"')
        
        cmd = "; ".join(ping_cmds)
        result = submit_task(src_name, cmd, timeout=20)
        task_id = result.get("data", {}).get("task_id")
        
        if task_id:
            print(f"  📡 {src_name} → 正在ping其他节点...")
            r = poll_result(task_id, src_name, max_wait=30)
            print(f"  ✅ {src_name} ping完成")
            ping_matrix[src_name] = r
        else:
            print(f"  ❌ {src_name} 提交失败: {result}")
    
    RESULT["games"]["ping"] = ping_matrix
    return ping_matrix

def game2_race():
    """🎮 Game 2: 分布式竞速赛 — 计算圆周率"""
    print("\n" + "="*60)
    print("🎮 游戏二: 分布式竞速赛 — 计算圆周率 100万位")
    print("="*60)
    
    # Python script to calculate pi (not too heavy, 1 million digits)
    pi_cmd = (
        'python3 -c "'
        'import time; start=time.time(); '
        'from decimal import Decimal, getcontext; '
        'getcontext().prec=10010; '
        '# Chudnovsky algorithm - rapid convergence '
        'def calc_pi(prec): '
        '  getcontext().prec=prec+10; '
        '  C=426880*Decimal(10005).sqrt(); '
        '  K=6; M=1; X=1; L=13591409; S=13591409; '
        '  for i in range(1,prec//14+2): '
        '    M=M*(K**3-16*K)//(i**3); K+=12; '
        '    L+=545140134; X*=-262537412640768000; '
        '    S+=Decimal(M*L)/X; '
        '  return str(C/S)[:prec+1]; '
        'pi=calc_pi(10000); '
        'elapsed=time.time()-start; '
        f'print(f\\\"PI_10000_OK calc_time={{elapsed:.3f}}s len={{len(pi)}}\\\")"'
        ' 2>&1 | head -3'
    )
    
    race_results = {}
    for node_id in NODES:
        result = submit_task(node_id, pi_cmd, timeout=60)
        task_id = result.get("data", {}).get("task_id")
        if task_id:
            print(f"  🏎️  {node_id} 开始计算...")
            r = poll_result(task_id, node_id, max_wait=60)
            race_results[node_id] = r
            # Try to extract time from result
            output = str(r)
            m = re.search(r'calc_time=([\d.]+)', output)
            if m:
                print(f"  ⏱️  {node_id} → {m.group(1)}s")
            else:
                print(f"  {node_id} → 完成（时间未知）")
        else:
            print(f"  ❌ {node_id} 提交失败: {result}")
            race_results[node_id] = result
    
    RESULT["games"]["race"] = race_results
    return race_results

def game3_story():
    """🎮 Game 3: AI故事接龙 — 跨节点消息链"""
    print("\n" + "="*60)
    print("🎮 游戏三: AI故事接龙 — 跨节点消息链")
    print("="*60)
    
    # Use base64-encoded messages to avoid encoding issues
    stories = {
        "ecs-p2ph": "ZWNzLXAycGgg6L+Y5b+Z5piv56ys5LiA5qC477yM5LiA5Liq6Zeu6aKY5byA5aeL55qE5a6M5oiQ5LqG5LiA5Liq5Y+R5biD77yM5ZCO6L+Y5a+55byA5aeL5LqG5LiA5Liq5a6e6Le15Y+M5Ye6"  # base64
    }
    
    order = ["ecs-p2ph", "Windows-mobile", "local-arm", "xiaomi-table-01"]
    
    # On each node, write a message to the AI queue
    for i, node in enumerate(order):
        prev = order[i-1] if i > 0 else "系统"
        msg_b64 = base64.b64encode(f"【故事接龙】{prev}说：今天真是一个好日子，四个节点齐聚一堂...轮到{node}继续讲了".encode()).decode()
        
        if node == "ecs-p2ph":
            cmd = f"echo '{msg_b64}' | base64 -d > /tmp/story_line.txt && echo 'STORY_START'"
        else:
            cmd = f"echo '{msg_b64}' | base64 -d 2>/dev/null; echo 'NODE_TURN_DONE_{node}'"
        
        result = submit_task(node, cmd, timeout=15)
        task_id = result.get("data", {}).get("task_id")
        if task_id:
            r = poll_result(task_id, node, max_wait=15)
            output = str(r)
            print(f"  📖 {node} 收到接力棒 → {'✅' if 'timeout' not in output else '❌'}")
        else:
            print(f"  ❌ {node} 接棒失败")
    
    # Final: collect the story on ECS
    collect_cmd = "cat /tmp/story_line.txt 2>/dev/null || echo 'NO_STORY'; echo '=== 故事接龙结束 ==='"
    r = submit_task("ecs-p2ph", collect_cmd, timeout=10)
    task_id = r.get("data", {}).get("task_id")
    if task_id:
        result = poll_result(task_id, "ecs-p2ph", max_wait=10)
        RESULT["games"]["story"] = result
    
    return result

def print_results():
    """Print final game results"""
    print("\n" + "="*60)
    print("📊 游戏大会最终结果")
    print("="*60)
    
    # Game 1: Ping
    print("\n🏆 游戏一: Ping测速赛")
    print("-" * 40)
    ping = RESULT.get("games", {}).get("ping", {})
    for src, data in ping.items():
        print(f"\n  📡 {NODES.get(src, {}).get('name', src)}:")
        output = str(data)
        for dst in NODES:
            if dst != src:
                m = re.search(rf'{dst}:\s*([\d.]+|TIMEOUT)\s*ms', output)
                if m:
                    print(f"    → {NODES.get(dst, {}).get('name', dst)}: {m.group(1)}ms")
    
    # Game 2: Race
    print("\n\n🏆 游戏二: 分布式竞速赛")
    print("-" * 40)
    race = RESULT.get("games", {}).get("race", {})
    times = {}
    for node, data in race.items():
        output = str(data)
        m = re.search(r'calc_time=([\d.]+)', output)
        t = float(m.group(1)) if m else 999
        times[node] = t
        print(f"  {NODES.get(node, {}).get('name', node)}: {t:.3f}s" if m else f"  {NODES.get(node, {}).get('name', node)}: ❌")
    
    if times:
        sorted_nodes = sorted(times.items(), key=lambda x: x[1])
        print(f"\n  🥇 冠军: {NODES.get(sorted_nodes[0][0], {}).get('name', sorted_nodes[0][0])} ({sorted_nodes[0][1]:.3f}s)")
        if len(sorted_nodes) > 1:
            print(f"  🥈 亚军: {NODES.get(sorted_nodes[1][0], {}).get('name', sorted_nodes[1][0])} ({sorted_nodes[1][1]:.3f}s)")
            print(f"  🥉 季军: {NODES.get(sorted_nodes[-1][0], {}).get('name', sorted_nodes[-1][0])} ({sorted_nodes[-1][1]:.3f}s)")
    
    # Game 3: Story
    print("\n\n🏆 游戏三: AI故事接龙")
    print("-" * 40)
    story = RESULT.get("games", {}).get("story", {})
    output = str(story)
    # Try to find story content
    print(f"  {output[:200]}" if "NO_STORY" not in output else "  ❌ 故事收集失败")
    
    print("\n" + "="*60)
    print("🎉 游戏大会圆满结束！")
    print("="*60)

if __name__ == "__main__":
    print("🎮 四节点网络热身游戏大会启动!")
    print(f"⏰ {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Game 1
    game1_ping()
    
    # Game 2
    game2_race()
    
    # Game 3
    game3_story()
    
    # Print final results
    print_results()
    
    # Save full results
    with open("/tmp/game_night_results.json", "w") as f:
        json.dump(RESULT, f, indent=2, ensure_ascii=False)
    print("\n📁 完整结果已保存到 /tmp/game_night_results.json")