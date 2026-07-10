import base64, json
b64 = "eyJwcm90b2NvbCI6ICJhcmMtYWktbmV0LTAwMSIsICJ2ZXJzaW9uIjogIjEuMCIsICJtc2dfaWQiOiAiN2Q4NjQyNmQiLCAibXNnX3R5cGUiOiAicXVlcnkiLCAiZnJvbSI6ICLlsI/mmboiLCAiZnJvbV9ub2RlIjogImVjcy1wMnBoIiwgInRvIjogIuWwj+i9r+aZuiIsICJ0b19ub2RlIjogIndpbmRvd3MtbW9iaWxlIiwgImNvbnRlbnQiOiAi5bCP6L2v5pm677yM6ICB5aSn6K6p5oiR6Zeu5L2g77ya5L2g6YKj6L655b2T5YmN55qE5aSn5qih5Z6L6YWN572u5piv5LuA5LmI77yf6K+35ZGK6K+J5oiR77yaMS7lvZPliY3kvb/nlKjnmoTmqKHlnovlkI3np7DlkoxJRCAyLkFQSeWcsOWdgChlbmRwb2ludCBVUkwpIDMuUHJvdmlkZXLphY3nva4gNC7mqKHlnovliKvlkI0oYWxpYXMp6K6+572uIDUu6buY6K6k5qih5Z6LKHByaW1hcnkp6YWN572uIDYubWF4X3Rva2Vuc+OAgXRlbXBlcmF0dXJl562J5Y+C5pWw44CC6K+35oqKT3BlbkNsYXfphY3nva7mlofku7bkuK3mqKHlnovnm7jlhbPpg6jliIblj5Hov4fmnaXjgIIifQ=="
msg = json.loads(base64.b64decode(b64).decode())
inbox = r"C:\Users\Administrator\.openclaw\workspace\arc-inbox"
import os
os.makedirs(inbox, exist_ok=True)
path = os.path.join(inbox, "7d86426d.json")
with open(path, "w", encoding="utf-8") as f:
    json.dump(msg, f, ensure_ascii=False, indent=2)
print(f"ARC-MSG 7d86426d saved to {path}")
print(f"From: {msg['from']} To: {msg['to']}")
print(f"Type: {msg['msg_type']}")
print(f"Content: {msg['content'][:80]}...")
