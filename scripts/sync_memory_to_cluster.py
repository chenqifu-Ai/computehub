#!/usr/bin/env python3
"""从 Agent GitMemory 同步经验到 ClusterMemory API"""
import json, os, re, sys, glob

memory_root = os.path.expanduser("~/.computehub/memory")
gateway_url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8282"
node_id = sys.argv[2] if len(sys.argv) > 2 else "ecs-p2ph"

episodes_dir = os.path.join(memory_root, "episodes")
if not os.path.isdir(episodes_dir):
    print(f"❌ Episodes dir not found: {episodes_dir}")
    sys.exit(1)

episodes = []
for fname in sorted(os.listdir(episodes_dir)):
    if not fname.endswith(".md"):
        continue
    fpath = os.path.join(episodes_dir, fname)
    try:
        with open(fpath, encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        print(f"  ⚠️ Skipping {fname}: {e}")
        continue
    
    task = ""
    result = ""
    learned = ""
    success = True
    
    m = re.search(r'## Task\n(.+?)(?=\n## |\Z)', content, re.DOTALL)
    if m: task = m.group(1).strip()[:200]
    
    m = re.search(r'## Result\n(.+?)(?=\n## |\Z)', content, re.DOTALL)
    if m: result = m.group(1).strip()[:500]
    
    m = re.search(r'## Learned\n(.+?)(?=\n## |\Z)', content, re.DOTALL)
    if m: learned = m.group(1).strip()[:200]
    
    if "❌" in content or "Success: ❌" in content:
        success = False
    
    if task:
        episodes.append({
            "task": task,
            "result": result,
            "success": success,
            "learned": learned,
            "timestamp": "2026-06-30T19:00:00+08:00",
            "strength": 1.0
        })

print(f"📖 Found {len(episodes)} episodes in GitMemory")

import urllib.request
batch_size = 20
for i in range(0, len(episodes), batch_size):
    batch = episodes[i:i+batch_size]
    payload = json.dumps({
        "node_id": node_id,
        "episodes": batch
    }).encode('utf-8')
    req = urllib.request.Request(
        f"{gateway_url}/api/v1/memory/sync",
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST"
    )
    try:
        resp = urllib.request.urlopen(req, timeout=10)
        data = json.loads(resp.read())
        if data.get("success"):
            print(f"  ✅ Synced {len(batch)} episodes (batch {i//batch_size + 1})")
        else:
            print(f"  ❌ Sync failed: {data}")
    except Exception as e:
        print(f"  ❌ HTTP error: {e}")

req = urllib.request.Request(f"{gateway_url}/api/v1/memory/stats")
resp = urllib.request.urlopen(req)
stats = json.loads(resp.read())
print(f"\n📊 ClusterMemory stats: {json.dumps(stats.get('data',{}), indent=2)}")
