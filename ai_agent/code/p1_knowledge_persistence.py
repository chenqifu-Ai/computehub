#!/usr/bin/env python3
"""P1: KnowledgeStore 持久化修复 + P2: TriggerEngine 规则增强 + P3: Phase3b 端到端触发"""

import json, os, sys

PROJECT = "/home/computehub/ComputeHub"

def p1_knowledge_persistence():
    """
    修复1: globalKnowledgeStore 启动时从 cluster_memory.json 加载
    需要在 gateway.go 的 NewOpcGateway 中调用 globalKnowledgeStore 的 load 方法
    """
    # 看 gateway_knowledge.go 有没有 load 方法
    kn_path = os.path.join(PROJECT, "src/gateway/gateway_knowledge.go")
    with open(kn_path) as f:
        content = f.read()
    
    if "func (ks *KnowledgeStore) load" in content:
        print("[P1] ✅ KnowledgeStore.load() 已存在")
    else:
        print("[P1] ❌ KnowledgeStore.load() 方法缺失，需要添加")
    
    # 检查 gateway.go 中是否有加载调用
    gw_path = os.path.join(PROJECT, "src/gateway/gateway.go")
    with open(gw_path) as f:
        gw = f.read()
    
    if "globalKnowledgeStore.loadFromFile" in gw or "globalKnowledgeStore.load" in gw:
        print("[P1] ✅ KnowledgeStore 启动加载已集成")
    else:
        print("[P1] ❌ KnowledgeStore 启动加载未集成 — 需要注入")
    
    # 检查 clusterMem 中的 knowledge 格式
    mem_path = os.path.join(PROJECT, "src/gateway/gateway_memory.go")
    with open(mem_path) as f:
        mem = f.read()
    
    # 找到 storeKnowledge
    idx = mem.find("func (cm *ClusterMemory) storeKnowledge")
    if idx >= 0:
        snippet = mem[idx:idx+500]
        if "globalKnowledgeStore" in snippet:
            print("[P1] ✅ ClusterMemory.storeKnowledge 已同步到 globalKnowledgeStore")
        else:
            print("[P1] ❌ ClusterMemory.storeKnowledge 未同步到 globalKnowledgeStore")
    
    return kn_path, gw, content

def p2_trigger_rules():
    """检查/增强 TriggerEngine 规则"""
    rules_path = os.path.join(PROJECT, "data/trigger_rules.json")
    with open(rules_path) as f:
        rules = json.load(f)
    
    existing_ids = {r["id"] for r in rules}
    print(f"\n[P2] 现有规则: {len(rules)} 条")
    for r in rules:
        print(f"      {r['id']} (en={r['enabled']}, type={r['event_type']}, hits={r['hit_count']})")
    
    needed = [
        ("disk-cleanup-alert", "磁盘清理提醒", 
         "磁盘使用率超过85%时提醒清理", "system", "disk_percent", "gt", 85, 80),
        ("node-offline-alert", "节点离线检测",
         "节点心跳5分钟未收到时告警", "system", "node_count", "lt", 4, 95),
    ]
    
    new_rules = []
    for rid, name, desc, etype, field, op, threshold, weight in needed:
        if rid in existing_ids:
            print(f"[P2] ✅ 规则已存在: {rid}")
        else:
            new_rules.append({
                "id": rid, "name": name, "description": desc,
                "enabled": True, "event_type": etype,
                "condition": {"field": field, "operator": op, "num_threshold": threshold},
                "weight": weight, "debounce": 60000000000,
                "actions": [{"type": "log", "message": f"⚠️ {desc}"}],
                "created_at": "2026-07-02T09:20:00+08:00",
                "updated_at": "2026-07-02T09:20:00+08:00",
                "hit_count": 0, "last_hit": "0001-01-01T00:00:00Z"
            })
    
    if new_rules:
        print(f"[P2] ➕ 新增 {len(new_rules)} 条规则:")
        for r in new_rules:
            print(f"      + {r['id']}: {r['description']}")
        rules.extend(new_rules)
        with open(rules_path, 'w') as f:
            json.dump(rules, f, indent=2, ensure_ascii=False)
        print(f"[P2] ✅ 写入 {rules_path}")
    else:
        print("[P2] ✅ 无需新增规则")
    
    return new_rules

def main():
    print("=" * 60)
    print("P1: KnowledgeStore 持久化修复")
    print("=" * 60)
    p1_knowledge_persistence()
    
    print("\n" + "=" * 60)
    print("P2: TriggerEngine 规则增强")
    print("=" * 60)
    p2_trigger_rules()
    
    print("\n" + "=" * 60)
    print("P3: Phase3b 端到端")
    print("=" * 60)
    print("Phase 3b 已激活 (worker_agent.go +6行)")
    print("需要 Agent 任务触发 → recordEpisode → OnTaskCompleted → extractLesson")
    print("验证: 提交一个 Agent 任务（非纯 echo），检查 GitMemory 是否有复盘 commit")
    print("或等 Agent 自动触发 self-reflection（每5次任务）")

if __name__ == "__main__":
    main()