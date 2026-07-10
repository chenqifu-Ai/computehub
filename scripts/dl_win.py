import urllib.request, hashlib, os, sys

ver = "1.3.17"
url = sys.argv[1] if len(sys.argv) > 1 else "http://36.250.122.43:8282/api/v1/download?file=computehub-windows-amd64.exe"
expected = sys.argv[2] if len(sys.argv) > 2 else "71faf32cd8c98e156f28ea13306bd0a91d81f1383f877639216188007c5f1826"

print("DL", ver, url)
data = urllib.request.urlopen(url, timeout=120).read()
h = hashlib.sha256(data).hexdigest()
print("GOT", len(data), "bytes SHA256:", h)

if h == expected:
    path = "C:\\Windows\\Temp\\ch-v1.3.17.exe"
    with open(path, "wb") as f:
        f.write(data)
    print("SHA256_MATCH")
else:
    print("SHA256_MISMATCH expected=" + expected)
