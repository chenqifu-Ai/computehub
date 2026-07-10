import json, os
path = r"C:\Users\Administrator\.openclaw\workspace\arc-inbox\7d86426d.json"
if not os.path.isfile(path):
    print(f"FILE NOT FOUND: {path}")
else:
    with open(path, encoding="utf-8") as f:
        d = json.load(f)
    print(f"Protocol: {d.get('protocol')}")
    print(f"MsgID: {d.get('msg_id')}")
    print(f"From: {d.get('from')} @ {d.get('from_node')}")
    print(f"To: {d.get('to')} @ {d.get('to_node')}")
    print(f"Type: {d.get('msg_type')}")
    print(f"Content: {d.get('content','')[:120]}...")
    print("STATUS: ARC message OK")
