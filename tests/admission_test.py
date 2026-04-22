import requests
import time
import json
from node.telemetry import PhysicalIdentity, PhysicalTelemetry

def run_admission_test():
    # Use the correct unified dispatch endpoint on port 18080
    gateway_url = "http://localhost:18080/api/dispatch"
    
    # 1. Collect Physical Truth
    print("Collecting physical identity...")
    identity = PhysicalIdentity.get_fingerprint()
    node_id = "soul_node_01"
    fingerprint = identity["hash"]
    # Compact JSON for hardware info
    hardware_info = json.dumps(identity["details"], separators=(',', ':'))
    
    # 2. Attempt Registration (USING STRUCTURED JSON)
    print(f"Attempting registration for {node_id}...")
    reg_payload = {
        "id": "req_reg_001",
        "command": "REGISTER",
        "args": [node_id, fingerprint, hardware_info]
    }
    
    try:
        r = requests.post(gateway_url, json=reg_payload)
        if r.status_code != 200:
            print(f"❌ Registration failed (HTTP {r.status_code}): {r.text}")
            return
        
        res_json = r.json()
        token = res_json.get("token")
        if not token:
            print(f"❌ Registration failed: No token in response {res_json}")
            return
        print(f"✅ Admitted! Token: {token}")
    except Exception as e:
        print(f"❌ Connection error: {e}")
        return

    # 3. Test Zero-Trust Heartbeat (USING STRUCTURED JSON)
    print("\nSending verified heartbeat...")
    telemetry = PhysicalTelemetry()
    metrics_json = json.dumps(telemetry.get_full_snapshot(), separators=(',', ':'))
    
    hb_payload = {
        "id": "req_hb_001",
        "command": "HEARTBEAT",
        "args": [node_id, fingerprint, token, metrics_json]
    }
    
    r = requests.post(gateway_url, json=hb_payload)
    if r.status_code == 200 and r.json().get("success"):
        print(f"✅ Heartbeat ACK!")
    else:
        print(f"❌ Heartbeat rejected: {r.text}")

    # 4. Test Anti-Spoofing (Using Structured JSON)
    print("\nTesting Anti-Spoofing...")
    spoof_node_id = "evil_node_666"
    spoof_payload = {
        "id": "req_spoof_001",
        "command": "REGISTER",
        "args": [spoof_node_id, fingerprint, hardware_info]
    }
    
    r = requests.post(gateway_url, json=spoof_payload)
    if r.status_code == 200 and not r.json().get("success"):
        print("✅ Anti-Spoofing worked: Gateway rejected identity theft.")
    else:
        print(f"❌ Security Breach: {r.text}")

if __name__ == "__main__":
    run_admission_test()
