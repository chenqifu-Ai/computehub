#!/usr/bin/env python3
"""Connect to ECS gateway WebSocket and generate pairing setup code"""
import socket, base64, json, time, struct, sys, random, select

HOST = '127.0.0.1'
PORT = 18789
TOKEN = "146aaa219c512bd2495e24d4ffb0c6f1422e5767be997351"

def rx(s, n):
    d = b''
    while len(d) < n:
        c = s.recv(n - len(d))
        if not c: raise ConnectionError()
        d += c
    return d

def sf(s, p):
    f = bytearray([0x81])
    l = len(p)
    if l < 126: f.append(l)
    elif l < 65536: f.extend([126, l>>8, l&0xFF])
    else: f.extend([127] + l.to_bytes(8, 'big'))
    f.extend(p)
    s.sendall(f)

def rf(s):
    b0,b1 = rx(s, 2)
    l = b1 & 0x7F
    if l == 126: l = struct.unpack('>H', rx(s, 2))[0]
    elif l == 127: l = struct.unpack('>Q', rx(s, 8))[0]
    m = rx(s, 4) if (b1 & 0x80) else b''
    p = rx(s, l)
    if m: p = bytes(b ^ m[i%4] for i,b in enumerate(p))
    return b0 & 0x0F, p

s = socket.socket()
s.settimeout(8)
s.connect((HOST, PORT))
k = base64.b64encode(bytes(random.randint(0,255) for _ in range(16))).decode()
upg = "GET / HTTP/1.1\r\nHost: {}:{}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {}\r\nSec-WebSocket-Version: 13\r\n\r\n".format(HOST, PORT, k)
s.sendall(upg.encode())
rx(s, 4096)

op, p = rf(s)
chal = json.loads(p)
nonce = chal['payload']['nonce']
sys.stderr.write("C\n")

auth = json.dumps({"type":"request","id":"auth","method":"connect.auth","params":{"nonce":nonce,"token":TOKEN}})
sf(s, auth.encode())
time.sleep(0.5)
ready = select.select([s], [], [], 3)
if ready[0]:
    op, p2 = rf(s)
    if op == 8:
        sys.stderr.write("X:" + p2.decode()[:100] + "\n")
    else:
        r2 = json.loads(p2)
        sys.stderr.write("A:" + json.dumps(r2)[:100] + "\n")
        if r2.get('type') == 'result':
            req2 = json.dumps({"type":"request","id":"1","method":"device.token.rotate","params":{}})
            sf(s, req2.encode())
            time.sleep(1)
            ready2 = select.select([s], [], [], 3)
            if ready2[0]:
                op, p3 = rf(s)
                if op == 1:
                    r3 = json.loads(p3)
                    print(json.dumps(r3))
else:
    sys.stderr.write("T\n")
s.close()