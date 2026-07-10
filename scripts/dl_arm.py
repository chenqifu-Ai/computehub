import urllib.request, os
d = urllib.request.urlopen("http://36.250.122.43:8282/api/v1/download?file=computehub-linux-arm64.exe", timeout=120).read()
path = "/data/data/com.termux/files/home/OPC/ch-v1.3.17"
with open(path, "wb") as f: f.write(d)
os.chmod(path, 0o755)
print("OK", len(d), "bytes")
