#!/usr/bin/env python3
"""
Fix v1.3.26 remote upgrade issues:
1. Recompile ALL platform binaries correctly (no more x86-64 on ARM/Windows)
2. Fix SHA256 checksums
3. Clean up deploy/ directory
"""
import os
import subprocess
import hashlib
import shutil
import sys

ROOT = "/home/computehub/ComputeHub"
DEPLOY = os.path.join(ROOT, "deploy")
VERSION = "1.3.26"

def run(cmd, cwd=ROOT):
    print(f"  > {cmd}")
    r = subprocess.run(cmd, shell=True, cwd=cwd, capture_output=True, text=True)
    if r.returncode != 0:
        print(f"  ❌ FAILED: {r.stderr}")
    return r.returncode == 0

def sha256_file(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            h.update(chunk)
    return h.hexdigest()

def main():
    print(f"🔧 Fixing v{VERSION} remote upgrade...")
    print()

    # ── Step 1: Build all platforms correctly ──
    print("=== Step 1: Cross-compile all platforms ===")
    ldflags = f'-s -w -X github.com/computehub/opc/src/version.VERSION={VERSION}'

    # Linux amd64
    if run(f"go build -o {DEPLOY}/computehub-linux-amd64 -ldflags=\"{ldflags}\" -buildvcs=false -trimpath ./cmd/computehub/"):
        print("  ✅ linux-amd64 compiled")
    else:
        print("  ❌ linux-amd64 FAILED")
        return 1

    # Linux arm64
    if run(f"GOARCH=arm64 go build -o {DEPLOY}/computehub-linux-arm64 -ldflags=\"{ldflags}\" -buildvcs=false -trimpath ./cmd/computehub/"):
        print("  ✅ linux-arm64 compiled")
    else:
        print("  ❌ linux-arm64 FAILED")
        return 1

    # Windows amd64
    if run(f"GOOS=windows GOARCH=amd64 go build -o {DEPLOY}/computehub-windows-amd64.exe -ldflags=\"{ldflags}\" -buildvcs=false -trimpath ./cmd/computehub/"):
        print("  ✅ windows-amd64 compiled")
    else:
        print("  ❌ windows-amd64 FAILED")
        return 1

    print()

    # ── Step 2: Verify binaries ──
    print("=== Step 2: Verify binaries ===")
    bin_files = {
        "linux-amd64": f"{DEPLOY}/computehub-linux-amd64",
        "linux-arm64": f"{DEPLOY}/computehub-linux-arm64",
        "windows-amd64": f"{DEPLOY}/computehub-windows-amd64.exe",
    }
    for name, path in bin_files.items():
        r = subprocess.run(f"file {path}", shell=True, capture_output=True, text=True)
        size = os.path.getsize(path)
        sha = sha256_file(path)
        print(f"  {name:15s} {size:>10d} bytes  SHA256={sha[:16]}...  {r.stdout.strip()}")
    print()

    # ── Step 3: Update deploy/1.3.26/ structure ──
    print("=== Step 3: Update deploy/1.3.26/ ===")
    v_dir = os.path.join(DEPLOY, VERSION)
    if os.path.exists(v_dir):
        shutil.rmtree(v_dir)
    os.makedirs(os.path.join(v_dir, "linux-amd64"), exist_ok=True)
    os.makedirs(os.path.join(v_dir, "linux-arm64"), exist_ok=True)
    os.makedirs(os.path.join(v_dir, "windows-amd64"), exist_ok=True)

    # Copy binaries to versioned dir
    shutil.copy2(bin_files["linux-amd64"], os.path.join(v_dir, "linux-amd64", "computehub"))
    shutil.copy2(bin_files["linux-arm64"], os.path.join(v_dir, "linux-arm64", "computehub"))
    shutil.copy2(bin_files["windows-amd64"], os.path.join(v_dir, "windows-amd64", "computehub.exe"))

    print("  ✅ deploy/1.3.26/ structure created")
    print()

    # ── Step 4: Fix SHA256 checksums ──
    print("=== Step 4: Fix SHA256 checksums ===")

    # sha256sums.txt (root-level)
    sha_data = ""
    for name, path in bin_files.items():
        sha = sha256_file(path)
        filename = os.path.basename(path)
        sha_data += f"{sha}  {filename}\n"
    with open(os.path.join(DEPLOY, "sha256sums.txt"), "w") as f:
        f.write(sha_data)
    print("  ✅ sha256sums.txt")

    # sha256sums-1.3.26.txt (versioned)
    versioned_sha = ""
    for plat, bname in [("linux-amd64", "computehub"), ("linux-arm64", "computehub"), ("windows-amd64", "computehub.exe")]:
        path = os.path.join(v_dir, plat, bname)
        sha = sha256_file(path)
        versioned_sha += f"{sha}  {plat}/{bname}\n"
    with open(os.path.join(DEPLOY, f"sha256sums-{VERSION}.txt"), "w") as f:
        f.write(versioned_sha)
    print("  ✅ sha256sums-1.3.26.txt")

    # Also fix deploy/linux-arm64/ (the symlink/copy used by download)
    os.makedirs(os.path.join(DEPLOY, "linux-arm64"), exist_ok=True)
    shutil.copy2(bin_files["linux-arm64"], os.path.join(DEPLOY, "linux-arm64", "computehub"))
    print("  ✅ deploy/linux-arm64/computehub updated with REAL arm64 binary")

    # Fix deploy/linux-amd64/
    os.makedirs(os.path.join(DEPLOY, "linux-amd64"), exist_ok=True)
    shutil.copy2(bin_files["linux-amd64"], os.path.join(DEPLOY, "linux-amd64", "computehub"))
    print("  ✅ deploy/linux-amd64/computehub updated")

    # Fix deploy/windows-amd64/
    os.makedirs(os.path.join(DEPLOY, "windows-amd64"), exist_ok=True)
    shutil.copy2(bin_files["windows-amd64"], os.path.join(DEPLOY, "windows-amd64", "computehub.exe"))
    print("  ✅ deploy/windows-amd64/computehub.exe updated with REAL PE binary")

    print()

    # ── Step 5: Verify download endpoint ──
    print("=== Step 5: Verify download endpoints ===")
    import urllib.request

    tests = [
        ("linux-arm64", "file=computehub&platform=linux/arm64"),
        ("windows-amd64", "file=computehub.exe&platform=windows/amd64"),
        ("linux-amd64", "file=computehub&platform=linux/amd64"),
    ]

    for plat_name, params in tests:
        url = f"http://localhost:8282/api/v1/download?{params}"
        try:
            resp = urllib.request.urlopen(url, timeout=10)
            data = resp.read()
            actual_sha = hashlib.sha256(data).hexdigest()
            expected_sha = sha256_file(bin_files[plat_name])
            match = "✅" if actual_sha == expected_sha else "❌"
            print(f"  {plat_name:15s} {len(data):>10d} bytes  {match} (SHA256 match={actual_sha == expected_sha})")
        except Exception as e:
            print(f"  {plat_name:15s} ❌ Error: {e}")

    print()

    # ── Step 6: Verify upgrade check ──
    print("=== Step 6: Verify upgrade check ===")
    for plat, node in [("linux/arm64", "worker-arm"), ("windows/amd64", "windows-mobile"), ("linux/amd64", "test")]:
        url = f"http://localhost:8282/api/v1/upgrade/check?current_version=1.3.25&platform={plat}&node_id={node}"
        try:
            resp = urllib.request.urlopen(url, timeout=10)
            import json
            data = json.loads(resp.read())
            print(f"  {plat:15s} update_available={data['data']['update_available']}  sha256={data['data']['sha256'][:16]}...")
        except Exception as e:
            print(f"  {plat:15s} ❌ Error: {e}")

    print()
    print("✅ Fix complete!")
    return 0

if __name__ == "__main__":
    sys.exit(main())
