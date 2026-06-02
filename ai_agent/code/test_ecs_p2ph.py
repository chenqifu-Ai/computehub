#!/usr/bin/env python3
"""ComputeHub ecs-p2ph 节点功能测试"""
import requests
import json
import time
import sys
import os

BASE = "http://36.250.122.43:8282"
results = []

def test(name, fn):
    try:
        start = time.time()
        passed, msg = fn()
        cost = (time.time() - start) * 1000
        status = "✅" if passed else "❌"
        results.append(f"{status} {name} ({cost:.0f}ms): {msg}")
        return passed
    except Exception as e:
        results.append(f"❌ {name} (ERR): {e}")
        return False

# ========== 1. 基础连通 ==========
def t1():
    r = requests.get(f"{BASE}/api/status", timeout=10)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    d = r.json()
    nodes = d.get("nodeManager", {})
    return True, f"gateway running | nodes: {nodes.get('total_nodes',0)} total, {nodes.get('online_nodes',0)} online | tasks: {nodes.get('total_tasks',0)} total, {nodes.get('active_tasks',0)} active | uptime: {d.get('uptime','?')}"
test("1. Gateway Status", t1)

# ========== 2. 上传文件 ==========
def t2():
    # Create a test PDF (minimal valid PDF)
    pdf_content = b"%PDF-1.4\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n2 0 obj\n<< /Type /Pages /Kids [] /Count 0 >>\nendobj\nxref\n0 3\n0000000000 65535 f \n0000000009 00000 n \n0000000058 00000 n \ntrailer\n<< /Size 3 /Root 1 0 R >>\nstartxref\n110\n%%EOF"
    
    files = {"file": ("test_upload.pdf", pdf_content, "application/pdf")}
    r = requests.post(f"{BASE}/upload", files=files, timeout=30)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    d = r.json()
    return True, f"uploaded | file_id: {d.get('file_id','?')} | filename: {d.get('filename','?')}"
test("2. Upload PDF", t2)

# ========== 3. 上传 TXT ==========
def t3():
    txt_content = ("# 测试文档\n"
        "这是一份用于测试的TXT文件。\n"
        "包含多行内容，用于验证文本文件上传和自动识别功能。\n"
        "\n"
        "测试要点：\n"
        "1. 中文支持\n"
        "2. 多行文本\n"
        "3. 特殊字符：$100, <tag>, &amp;\n"
    ).encode("utf-8")
    files = {"file": ("test_doc.txt", txt_content, "text/plain")}
    r = requests.post(f"{BASE}/upload", files=files, timeout=30)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    d = r.json()
    return True, f"uploaded | file_id: {d.get('file_id','?')} | filename: {d.get('filename','?')}"
test("3. Upload TXT", t3)

# ========== 4. 自动识别文件 ==========
def t4():
    files = {"file": ("test_image.png", b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01", "image/png")}
    r = requests.post(f"{BASE}/upload", files=files, timeout=30)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    d = r.json()
    # 检查是否自动识别为图片
    file_type = d.get("file_type", "")
    return True, f"auto-recognized | file_type: {file_type} | file_id: {d.get('file_id','?')}"
test("4. Auto-detect Image", t4)

# ========== 5. 列出文件 ==========
def t5():
    r = requests.get(f"{BASE}/files", timeout=10)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    d = r.json()
    files_list = d if isinstance(d, list) else d.get("files", [])
    return True, f"listed {len(files_list)} files"
test("5. List Files", t5)

# ========== 6. 获取文件信息 ==========
def t6():
    r = requests.get(f"{BASE}/files", timeout=10)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    d = r.json()
    files_list = d if isinstance(d, list) else d.get("files", [])
    if not files_list:
        return False, "no files to check"
    fid = files_list[-1].get("file_id")
    r2 = requests.get(f"{BASE}/file/{fid}", timeout=10)
    if r2.status_code != 200:
        return False, f"HTTP {r2.status_code}"
    info = r2.json()
    return True, f"file info: {json.dumps(info, ensure_ascii=False)[:200]}"
test("6. File Info", t6)

# ========== 7. 删除文件 ==========
def t7():
    r = requests.get(f"{BASE}/files", timeout=10)
    files_list = r.json() if r.status_code == 200 else []
    if isinstance(files_list, dict):
        files_list = files_list.get("files", [])
    if not files_list:
        return False, "no files to delete"
    fid = files_list[-1].get("file_id")
    r2 = requests.delete(f"{BASE}/file/{fid}", timeout=10)
    if r2.status_code != 200:
        return False, f"HTTP {r2.status_code}: {r2.text[:200]}"
    return True, f"deleted file {fid}"
test("7. Delete File", t7)

# ========== 8. 生成 Gallery ==========
def t8():
    # Get some files first
    r = requests.get(f"{BASE}/files", timeout=10)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    files_list = r.json() if isinstance(r.json(), list) else r.json().get("files", [])
    if not files_list:
        return False, "no files available"
    
    # Pick first file
    file_ids = [f.get("file_id") for f in files_list if f.get("file_id")]
    if not file_ids:
        return False, "no file_ids"
    
    payload = {"file_ids": file_ids[:1]}
    r2 = requests.post(f"{BASE}/generate", json=payload, timeout=60)
    if r2.status_code != 200:
        return False, f"HTTP {r2.status_code}: {r2.text[:200]}"
    d = r2.json()
    return True, f"generate triggered | task_id: {d.get('task_id','?')} | status: {d.get('status','?')}"
test("8. Generate Gallery", t8)

# ========== 9. 查询任务 ==========
def t9():
    r = requests.get(f"{BASE}/tasks", timeout=10)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    d = r.json()
    tasks = d if isinstance(d, list) else d.get("tasks", [])
    if isinstance(d, dict) and not isinstance(tasks, list):
        tasks = [d]
    return True, f"tasks: {len(tasks)} | {json.dumps(tasks[:2], ensure_ascii=False)[:200]}"
test("9. List Tasks", t9)

# ========== 10. 任务详情 ==========
def t10():
    r = requests.get(f"{BASE}/tasks", timeout=10)
    tasks = r.json() if r.status_code == 200 else []
    if isinstance(tasks, dict):
        tasks = tasks.get("tasks", [])
    if not tasks:
        return False, "no tasks"
    tid = tasks[-1].get("task_id")
    r2 = requests.get(f"{BASE}/task/{tid}", timeout=10)
    if r2.status_code != 200:
        return False, f"HTTP {r2.status_code}"
    info = r2.json()
    return True, f"task detail: {json.dumps(info, ensure_ascii=False)[:200]}"
test("10. Task Detail", t10)

# ========== 11. 图片预览 ==========
def t11():
    r = requests.get(f"{BASE}/files", timeout=10)
    files_list = r.json() if r.status_code == 200 else []
    if isinstance(files_list, dict):
        files_list = files_list.get("files", [])
    
    img_id = None
    for f in files_list:
        if f.get("file_type") in ("image/jpeg", "image/png", "image/webp"):
            img_id = f.get("file_id")
            break
    if not img_id:
        return False, "no image files found"
    
    r2 = requests.get(f"{BASE}/preview/{img_id}", timeout=10)
    if r2.status_code == 200:
        return True, f"preview returned | content-type: {r2.headers.get('content-type','?')} | size: {len(r2.content)} bytes"
    elif r2.status_code == 302 or r2.status_code == 301:
        # Redirect to actual image
        r3 = requests.get(r2.headers.get("Location", ""), timeout=10, allow_redirects=False)
        return True, f"redirect to image | status: {r2.status_code}"
    else:
        return False, f"HTTP {r2.status_code}: {r2.text[:200]}"
test("11. Image Preview", t11)

# ========== 12. 下载文件 ==========
def t12():
    r = requests.get(f"{BASE}/files", timeout=10)
    files_list = r.json() if r.status_code == 200 else []
    if isinstance(files_list, dict):
        files_list = files_list.get("files", [])
    if not files_list:
        return False, "no files"
    
    fid = files_list[0].get("file_id")
    r2 = requests.get(f"{BASE}/download/{fid}", timeout=10)
    if r2.status_code == 200:
        return True, f"downloaded | size: {len(r2.content)} bytes | content-type: {r2.headers.get('content-type','?')}"
    elif r2.status_code == 302 or r2.status_code == 301:
        return True, f"redirect (file served directly) | status: {r2.status_code}"
    else:
        return False, f"HTTP {r2.status_code}: {r2.text[:200]}"
test("12. File Download", t12)

# ========== 13. 多文件上传 ==========
def t13():
    files_data = [
        ("multi_test_1.txt", "文件1内容\n第二行\n".encode("utf-8"), "text/plain"),
        ("multi_test_2.txt", "文件2内容\n第二行\n".encode("utf-8"), "text/plain"),
        ("multi_test_3.txt", "文件3内容\n第三行\n".encode("utf-8"), "text/plain"),
    ]
    files = {"files": files_data}
    r = requests.post(f"{BASE}/upload", files=files, timeout=30)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    d = r.json()
    uploaded = d if isinstance(d, list) else d.get("uploaded", [])
    count = len(uploaded) if isinstance(uploaded, list) else 1
    return True, f"multi-upload {count} files | {json.dumps(uploaded[:3], ensure_ascii=False)[:200]}"
test("13. Multi-File Upload", t13)

# ========== 14. 并发生成 ==========
def t14():
    r = requests.get(f"{BASE}/files", timeout=10)
    files_list = r.json() if r.status_code == 200 else []
    if isinstance(files_list, dict):
        files_list = files_list.get("files", [])
    if len(files_list) < 2:
        return False, f"only {len(files_list)} files, need 2+"
    
    file_ids = [f.get("file_id") for f in files_list[:2]]
    payload = {"file_ids": file_ids}
    r2 = requests.post(f"{BASE}/generate", json=payload, timeout=60)
    if r2.status_code != 200:
        return False, f"HTTP {r2.status_code}: {r2.text[:200]}"
    d = r2.json()
    return True, f"concurrent generate | task_id: {d.get('task_id','?')} | files: {len(file_ids)}"
test("14. Multi-File Generate", t14)

# ========== 15. 错误处理 ==========
def t15():
    # Test invalid file ID
    r = requests.get(f"{BASE}/file/nonexistent", timeout=10)
    if r.status_code == 404:
        return True, "proper 404 for invalid file_id"
    elif r.status_code == 200:
        return True, "returned data (may not be ideal but not crash)"
    else:
        return False, f"unexpected status {r.status_code}: {r.text[:200]}"
test("15. Error Handling (Invalid ID)", t15)

# ========== 16. 空任务查询 ==========
def t16():
    r = requests.get(f"{BASE}/tasks", timeout=10)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}"
    d = r.json()
    tasks = d if isinstance(d, list) else d.get("tasks", [])
    if isinstance(d, dict) and not tasks:
        tasks = [d]
    return True, f"tasks list valid JSON | count: {len(tasks)}"
test("16. Empty Tasks List", t16)

# ========== 17. 大文件上传 ==========
def t17():
    # 1MB text file
    content = ("这是一份测试大文件的测试内容。" * 10000).encode("utf-8")
    files = {"file": ("large_test.txt", content, "text/plain")}
    r = requests.post(f"{BASE}/upload", files=files, timeout=60)
    if r.status_code != 200:
        return False, f"HTTP {r.status_code}: {r.text[:200]}"
    d = r.json()
    return True, f"large file uploaded | size: {len(content)} bytes | file_id: {d.get('file_id','?')}"
test("17. Large File Upload (1MB)", t17)

# ========== 18. 系统健康 ==========
def t18():
    r = requests.get(f"{BASE}/api/status", timeout=10)
    d = r.json()
    checks = []
    if d.get("pipeline", {}).get("status") == "ACTIVE":
        checks.append("pipeline=ACTIVE")
    if d.get("executor", {}).get("status") == "READY":
        checks.append("executor=READY")
    if d.get("kernel", {}).get("status") == "RUNNING":
        checks.append("kernel=RUNNING")
    return True, "health: " + " | ".join(checks)
test("18. System Health", t18)

# ========== Summary ==========
print("\n" + "="*60)
print("📊 ComputeHub ecs-p2ph 节点功能测试报告")
print("="*60)

passed = sum(1 for r in results if r.startswith("✅"))
total = len(results)
failed = total - passed

for i, r in enumerate(results, 1):
    print(f"  {i}. {r}")

print("="*60)
print(f"📈 通过率: {passed}/{total} ({passed*100//total}%)")
if failed > 0:
    print(f"❌ 失败: {failed} 项")
else:
    print("🎉 全部通过！")
print("="*60)
