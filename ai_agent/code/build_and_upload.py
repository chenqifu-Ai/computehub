#!/usr/bin/env python3
"""
ComputeHub 0.7.6 全平台编译 + 上传到 worker-localhost
策略: 本地交叉编译(更快) → 通过 Gateway 任务写入远程节点
"""
import json, os, subprocess, sys, time, re, urllib.request

# ==================== 配置 ====================
GATEWAY = "http://192.168.1.7:8282"
NODE_ID = "worker-localhost"
SOURCE_DIR = "/root/computehub-zero"
VERSION = "0.7.6"
OUTPUT_DIR = "/tmp/computehub-build"
REMOTE_DEST = "/root/computehub-builds"

BINS = ["gateway", "worker", "tui"]
PLATFORMS = [
    ("linux-amd64",  "linux",  "amd64",  ""),
    ("linux-arm64",  "linux",  "arm64",  ""),
    ("darwin-amd64", "darwin", "amd64",  ""),
    ("darwin-arm64", "darwin", "arm64",  ""),
    ("windows-amd64","windows","amd64",  ".exe"),
]

LD_FLAGS = f'-X github.com/computehub/opc/src/version.VERSION={VERSION}'

# ==================== 工具函数 ====================
def curl_task_submit(command, task_id):
    """通过 Gateway 提交任务"""
    body = json.dumps({
        "task_id": task_id,
        "command": command,
        "timeout": 60
    }).encode()
    req = urllib.request.Request(f"{GATEWAY}/api/v1/tasks/submit", data=body,
                                  headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data.get("success", False), data.get("error", "")
    except Exception as e:
        return False, str(e)

def curl_task_detail(task_id):
    """查询任务结果"""
    url = f"{GATEWAY}/api/v1/tasks/detail?task_id={task_id}&node_id={NODE_ID}"
    req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
            return data
    except Exception as e:
        return {"data": {"status": "error", "stdout": str(e)}}

def run_task(cmd, task_id, wait=65):
    """提交并等待任务完成"""
    print(f"  📤 提交任务: {task_id}")
    ok, err = curl_task_submit(cmd, task_id)
    if not ok:
        print(f"  ❌ 提交失败: {err}")
        return False, ""
    print(f"  ⏳ 等待完成... (约{wait}s)")
    time.sleep(wait)
    detail = curl_task_detail(task_id)
    d = detail.get("data", {})
    status = d.get("status", "unknown")
    exit_code = d.get("exit_code", -1)
    stdout = d.get("stdout", "")
    stderr = d.get("stderr", "")
    if status == "completed" and exit_code == 0:
        return True, stdout
    elif status == "running":
        return False, "任务仍在运行"
    else:
        return False, f"失败: {status} (exit={exit_code})\nSTDERR: {stderr[:500]}"

def upload_via_task(file_path, remote_path, task_id_prefix):
    """
    通过任务写入文件到远程节点
    使用 base64 + 分块写入
    """
    file_size = os.path.getsize(file_path)
    chunk_size = 4000  # 每 chunk 最多 4KB base64
    remote_dir = os.path.dirname(remote_path)
    
    # 创建目录
    print(f"  📤 创建目录: {remote_dir}")
    ok, _ = run_task(f"mkdir -p {remote_dir}", f"{task_id_prefix}-mkdir", wait=15)
    if not ok:
        return False
    
    # 分块写入
    with open(file_path, 'rb') as f:
        data = f.read()
    
    chunks = []
    for i in range(0, len(data), chunk_size):
        chunks.append(data[i:i+chunk_size])
    
    print(f"  📤 分 {len(chunks)} 块上传 ({file_size}B → {remote_path})")
    
    # 第一块用 >，后续用 >>
    for idx, chunk in enumerate(chunks):
        b64 = chunk.hex()  # 用 hex 编码避免 base64 换行问题
        task_id = f"{task_id_prefix}-chunk{idx}"
        if idx == 0:
            cmd = f'echo -n "{b64}" | xxd -r -p > "{remote_path}"'
        else:
            cmd = f'echo -n "{b64}" | xxd -r -p >> "{remote_path}"'
        
        ok, err = run_task(cmd, task_id, wait=35)
        if not ok:
            print(f"  ❌ 块 {idx} 失败: {err}")
            return False
    
    # 验证
    verify_task_id = f"{task_id_prefix}-verify"
    ok, result = run_task(
        f'ls -la "{remote_path}" && wc -c "{remote_path}"',
        verify_task_id, wait=15
    )
    if ok:
        print(f"  ✅ 上传完成: {result.strip()}")
    return True

def build_locally():
    """本地交叉编译所有平台/组件"""
    print("\n" + "=" * 55)
    print(f"  🔨 ComputeHub {VERSION} 全平台本地编译")
    print("=" * 55)
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    total = 0
    passed = 0
    failed = 0
    results = []
    
    for platform_name, goos, goarch, ext in PLATFORMS:
        for bin_name in BINS:
            total += 1
            out = os.path.join(OUTPUT_DIR, platform_name, f"computehub-{bin_name}{ext}")
            tmp = out + ".tmp"
            
            print(f"\n[{total}] {bin_name} → {platform_name}")
            
            os.makedirs(os.path.dirname(out), exist_ok=True)
            
            cmd = (
                f'cd {SOURCE_DIR} && '
                f'CGO_ENABLED=0 GOOS={goos} GOARCH={goarch} '
                f'go build -ldflags="{LD_FLAGS}" '
                f'-o "{tmp}" "./cmd/{bin_name}/" 2>&1'
            )
            
            try:
                result = subprocess.run(
                    cmd, shell=True, capture_output=True, text=True, timeout=120
                )
                if result.returncode == 0:
                    os.rename(tmp, out)
                    os.chmod(out, 0o755)
                    size_kb = os.path.getsize(out) / 1024
                    print(f"   ✅ {out} ({size_kb:.1f}KB)")
                    passed += 1
                    results.append((platform_name, bin_name, out, True))
                else:
                    print(f"   ❌ 编译失败")
                    print(f"   stderr: {result.stderr[:300]}")
                    failed += 1
                    results.append((platform_name, bin_name, out, False))
            except subprocess.TimeoutExpired:
                print(f"   ❌ 超时")
                failed += 1
                results.append((platform_name, bin_name, out, False))
    
    print("\n" + "=" * 55)
    print(f"  结果: {passed}/{total} 通过, {failed} 失败")
    print("=" * 55)
    
    return results, total, passed, failed

def sha256_file(path):
    """计算文件 SHA256"""
    import hashlib
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()

def main():
    # Step 1: 本地编译
    results, total, passed, failed = build_locally()
    
    if failed > 0:
        print(f"\n⚠️ 有 {failed} 个目标编译失败，是否继续上传成功的？(y/n): ", end="")
        answer = input().strip().lower()
        if answer != 'y':
            print("取消上传")
            return
    
    if passed == 0:
        print("❌ 没有成功的二进制，放弃")
        return
    
    # Step 2: 上传成功二进制到 worker-localhost
    print("\n" + "=" * 55)
    print(f"  📡 上传 {passed} 个二进制到 worker-localhost")
    print("=" * 55)
    
    upload_results = []
    for platform_name, bin_name, out_path, success in results:
        if not success:
            continue
        
        remote_path = f"{REMOTE_DEST}/{platform_name}/computehub-{bin_name}"
        print(f"\n📦 {platform_name}/{bin_name} ({os.path.getsize(out_path)}B)")
        
        ok = upload_via_task(out_path, remote_path, f"upload-{platform_name}-{bin_name}")
        if ok:
            # 远程验证
            verify_id = f"verify-{platform_name}-{bin_name}"
            ok, verify_out = run_task(
                f'cd {REMOTE_DEST}/{platform_name} && '
                f'chmod +x computehub-{bin_name} && '
                f'./computehub-{bin_name} --version 2>&1 | head -1 && '
                f'ls -la computehub-{bin_name}',
                verify_id, wait=30
            )
            if ok:
                print(f"  ✅ 远程验证: {verify_out.strip()[:100]}")
            else:
                print(f"  ⚠️ 远程验证失败: {verify_out[:200]}")
        else:
            print(f"  ❌ 上传失败")
        
        upload_results.append((platform_name, bin_name, ok))
    
    # Step 3: 生成报告
    print("\n" + "=" * 55)
    print("  📊 上传报告")
    print("=" * 55)
    
    success_count = sum(1 for _, _, ok in upload_results if ok)
    print(f"  上传成功: {success_count}/{len(upload_results)}")
    
    for platform_name, bin_name, ok in upload_results:
        status = "✅" if ok else "❌"
        print(f"  {status} {platform_name}/{bin_name}")
    
    # Step 4: 生成 sha256sums 本地备份
    sha_file = os.path.join(OUTPUT_DIR, f"sha256sums-{VERSION}.txt")
    print(f"\n📝 生成 sha256sums → {sha_file}")
    with open(sha_file, 'w') as f:
        for _, _, path, success in results:
            if success:
                h = sha256_file(path)
                rel = os.path.relpath(path, OUTPUT_DIR)
                f.write(f"{h}  {rel}\n")
    
    print(f"\n✅ 全部完成! 二进制在 {OUTPUT_DIR}/")
    print(f"   远程路径: {REMOTE_DEST}/")

if __name__ == "__main__":
    main()
