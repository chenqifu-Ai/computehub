import json, os, glob

outbox = r"C:\Users\Administrator\.openclaw\workspace\arc-outbox"
processed = r"C:\Users\Administrator\.openclaw\workspace\arc-outbox\.processed"

if not os.path.isdir(outbox):
    print("NO_REPLIES: arc-outbox directory not found")
    exit(0)

files = glob.glob(os.path.join(outbox, "*.json"))
processed_files = set()
if os.path.isfile(processed):
    with open(processed) as f:
        processed_files = set(f.read().strip().split("\n"))

new_replies = []
for fp in sorted(files):
    fname = os.path.basename(fp)
    if fname.startswith(".") or fname in processed_files:
        continue
    try:
        with open(fp, encoding="utf-8") as f:
            msg = json.load(f)
        if msg.get("protocol") == "arc-ai-net-001":
            new_replies.append({
                "file": fname,
                "from": msg.get("from", "?"),
                "type": msg.get("msg_type", "?"),
                "content": msg.get("content", "")
            })
    except:
        pass

if new_replies:
    print(f"NEW_REPLIES: {len(new_replies)}")
    for r in new_replies:
        print(f"---")
        print(f"File: {r['file']}")
        print(f"From: {r['from']}")
        print(f"Type: {r['type']}")
        print(f"Content: {r['content'][:500]}")
    
    # Mark as processed
    with open(processed, "a") as f:
        for r in new_replies:
            f.write(r['file'] + "\n")
else:
    print("NO_REPLIES")
