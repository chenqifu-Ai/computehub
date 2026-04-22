import requests
import json
import uuid

GATEWAY_URL = "http://127.0.0.1:18080/api/dispatch"

def test_gateway():
    print("🚀 Starting ComputeHub Gateway Integration Test...")
    
    node_id = "test_node_001"
    fingerprint = f"fp_{uuid.uuid4().hex[:8]}"
    hw_info = json.dumps({"cpu": "arm64", "ram": "4GB"})
    
    # 1. Test REGISTER
    print("\nTesting REGISTER...")
    reg_payload = {
        "command": "REGISTER",
        "args": [node_id, fingerprint, hw_info]
    }
    try:
        resp = requests.post(GATEWAY_URL, json=reg_payload)
        data = resp.json()
        if data.get("success"):
            token = data.get("token")
            print(f"✅ REGISTER Success! Token: {token}")
        else:
            print(f"❌ REGISTER Failed: {data.get('error')}")
            return
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # 2. Test HEARTBEAT
    print("\nTesting HEARTBEAT...")
    metrics = json.dumps({"cpu_usage": 15.5, "mem_usage": 40.2})
    hb_payload = {
        "command": "HEARTBEAT",
        "args": [node_id, fingerprint, token, metrics]
    }
    try:
        resp = requests.post(GATEWAY_URL, json=hb_payload)
        data = resp.json()
        if data.get("success"):
            print(f"✅ HEARTBEAT Success! Trust Level: {data['data']['trust_level']}")
        else:
            print(f"❌ HEARTBEAT Failed: {data.get('error')}")
            return
    except Exception as e:
        print(f"❌ Connection Error: {e}")
        return

    # 3. Test INVALID ARGS (Negative Test)
    print("\nTesting INVALID ARGS (Should fail)...")
    bad_payload = {
        "command": "REGISTER",
        "args": ["too_few"]
    }
    resp = requests.post(GATEWAY_URL, json=bad_payload)
    data = resp.json()
    if not data.get("success"):
        print(f"✅ Correctly rejected invalid args: {data.get('error')}")
    else:
        print("❌ Error: Gateway accepted invalid arguments!")

    print("\n✨ All basic gateway tests passed!")

if __name__ == "__main__":
    test_gateway()
