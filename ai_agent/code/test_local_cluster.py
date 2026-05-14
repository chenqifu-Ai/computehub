#!/usr/bin/env python3
"""Test local ComputeHub cluster node."""

import json
import subprocess
import time
import sys
from datetime import datetime

BASE_URL = "http://localhost:8282"

def run_cmd(cmd, timeout=10):
    """Run shell command and return result."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()
    except subprocess.TimeoutExpired:
        return -1, "", "Timeout"
    except Exception as e:
        return -1, "", str(e)

def http_get(path):
    """Make HTTP GET request."""
    rc, out, err = run_cmd(f'curl -s "{BASE_URL}{path}"')
    if rc != 0:
        return None
    try:
        return json.loads(out)
    except json.JSONDecodeError:
        return out

def test_health():
    """Test health endpoint."""
    print("=" * 60)
    print("🏥 1. HEALTH CHECK")
    print("=" * 60)
    data = http_get("/api/health")
    if data:
        print(f"   Health: {json.dumps(data, indent=2)}")
        return True
    print("   ❌ Health check failed")
    return False

def test_status():
    """Test status endpoint."""
    print("\n" + "=" * 60)
    print("📊 2. SYSTEM STATUS")
    print("=" * 60)
    data = http_get("/api/status")
    if data:
        print(f"   Uptime: {data.get('uptime', 'N/A')}")
        executor = data.get('executor', {})
        kernel = data.get('kernel', {})
        pipeline = data.get('pipeline', {})
        gene_store = data.get('geneStore', {})
        node_mgr = data.get('nodeManager', {})
        
        print(f"\n   Executor:")
        print(f"     Status: {executor.get('status', 'N/A')}")
        print(f"     Verification Rate: {executor.get('verification_rate', 0)}")
        print(f"     Sandbox Path: {executor.get('sandbox_path', 'N/A')}")
        
        print(f"\n   Kernel:")
        print(f"     Status: {kernel.get('status', 'N/A')}")
        print(f"     Queue Depth: {kernel.get('queue_depth', 0)}")
        print(f"     Schedule Latency: {kernel.get('schedule_latency', 'N/A')}")
        
        print(f"\n   Pipeline:")
        print(f"     Status: {pipeline.get('status', 'N/A')}")
        print(f"     Interceptions: {pipeline.get('interceptions', 0)}")
        
        print(f"\n   Gene Store:")
        print(f"     Size: {gene_store.get('size', 0)}")
        print(f"     Recall Rate: {gene_store.get('recall_rate', 0)}")
        
        print(f"\n   Node Manager:")
        print(f"     Total Nodes: {node_mgr.get('total_nodes', 0)}")
        print(f"     Online Nodes: {node_mgr.get('online_nodes', 0)}")
        print(f"     Total Tasks: {node_mgr.get('total_tasks', 0)}")
        print(f"     Active Tasks: {node_mgr.get('active_tasks', 0)}")
        print(f"     Nodes: {json.dumps(node_mgr.get('nodes', []), indent=6)}")
        return True
    print("   ❌ Status check failed")
    return False

def test_process_info():
    """Test local process info."""
    print("\n" + "=" * 60)
    print("⚙️ 3. LOCAL PROCESS INFO")
    print("=" * 60)
    
    # Check gateway process
    rc, out, err = run_cmd("ps aux | grep computehub-gateway | grep -v grep")
    if out:
        print(f"   Gateway process:\n   {out}")
    else:
        print("   ⚠️ Gateway process not found in ps")
    
    # Check worker process
    rc, out, err = run_cmd("ps aux | grep computehub-worker | grep -v grep")
    if out:
        print(f"   Worker process:\n   {out}")
    else:
        print("   ⚠️ Worker process not found in ps")
    
    # Check ports
    rc, out, err = run_cmd("netstat -tlnp 2>/dev/null | grep -E '8282|8283' || ss -tlnp 2>/dev/null | grep -E '8282|8283' || echo 'No port info'")
    if out:
        print(f"   Ports:\n   {out}")
    
    # Check worker log tail
    rc, out, err = run_cmd("tail -10 /tmp/computehub-worker.log 2>/dev/null || echo 'No worker log'")
    if out:
        print(f"   Worker log tail:\n   {out}")
    
    # Check gateway log
    rc, out, err = run_cmd("tail -10 gateway.log 2>/dev/null || echo 'No gateway log'")
    if out:
        print(f"   Gateway log tail:\n   {out}")
    
    return True

def main():
    print(f"🧪 ComputeHub Local Cluster Test")
    print(f"   Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"   Base URL: {BASE_URL}")
    
    results = {
        "health": test_health(),
        "status": test_status(),
        "process_info": test_process_info(),
    }
    
    print("\n" + "=" * 60)
    print("📋 SUMMARY")
    print("=" * 60)
    for test, passed in results.items():
        status = "✅" if passed else "❌"
        print(f"   {status} {test}")
    
    all_passed = all(results.values())
    print(f"\n   Overall: {'✅ ALL PASSED' if all_passed else '❌ SOME FAILED'}")
    return 0 if all_passed else 1

if __name__ == "__main__":
    sys.exit(main())
