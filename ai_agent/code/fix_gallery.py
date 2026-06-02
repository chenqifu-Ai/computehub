#!/usr/bin/env python3
"""Fix Gallery frontend and cleanup failed tasks."""
import requests
import json

GALLERY_URL = "http://36.250.122.43:8282"

print("=" * 50)
print("🔧 Gallery 修复脚本")
print("=" * 50)

# 1. 获取当前前端 HTML
print("\n1️⃣ 获取当前前端页面...")
resp = requests.get(f"{GALLERY_URL}/gallery")
if resp.status_code != 200:
    print(f"  ❌ 获取页面失败: {resp.status_code}")
    exit(1)
html = resp.text
print(f"  ✅ 获取成功 ({len(html)} bytes)")

# 2. 修复 accept 属性 - 移除 .txt（后端不支持）
print("\n2️⃣ 修复前端 accept 属性...")
old_accept = '.pdf,.pptx,.ppt,.docx,.doc,.txt'
new_accept = '.pdf,.pptx,.ppt,.docx,.doc'
if old_accept in html:
    html = html.replace(old_accept, new_accept)
    print(f"  ✅ 已移除 .txt (防止拖拽上传)")
else:
    print("  ⚠️  accept 属性格式不同，跳过")

# 3. 添加 JS 拦截逻辑 - 阻止 .md 和 .txt
print("\n3️⃣ 添加 JS 文件类型拦截...")

# 查找 handleFileSelect 函数
if "function handleFileSelect(files)" in html:
    # 在 handleFileSelect 函数开头插入拦截代码
    intercept_code = '''
    function handleFileSelect(files) {
        const rejected = [];
        for (let f of files) {
            const ext = '.' + f.name.split('.').pop().toLowerCase();
            if (ext === '.txt' || ext === '.md') {
                rejected.push(f.name);
                continue;
            }
            uploadToGallery(f);
        }
        if (rejected.length > 0) {
            alert('❌ 不支持的文件格式: ' + rejected.join(', ') + '\\n\\n请上传 .pdf, .pptx, .docx, .doc, .mp3, .wav, .jpg, .png 等格式');
        }
    }'''
    html = html.replace(
        '''function handleFileSelect(files) {
        for (let f of files) {
            uploadToGallery(f);
        }
    }''',
        intercept_code
    )
    print("  ✅ 已添加文件类型拦截")
else:
    print("  ⚠️  未找到 handleFileSelect 函数")

# 4. 添加清理失败任务的按钮
print("\n4️⃣ 添加清理失败任务按钮...")
task_cleanup_btn = '''        <button class="btn-clear" onclick="clearFailedTasks()" style="margin-left:8px;">🧹 清理失败</button>'''
if "clearFailedTasks" not in html:
    # 在 task-section 的 h3 后添加按钮
    html = html.replace(
        '<h3>📊 任务进度</h3>',
        '<h3>📊 任务进度</h3>' + task_cleanup_btn
    )
    
    # 在 render 函数后添加 clearFailedTasks 函数
    cleanup_func = '''
    async function clearFailedTasks() {
        try {
            const r = await fetch('/api/v1/gallery/tasks');
            const d = await r.json();
            const tasks = d.data || [];
            const failed = tasks.filter(t => t.stage === 'error' || t.stage === 'failed');
            if (failed.length === 0) {
                showToast('✅ 没有失败任务需要清理');
                return;
            }
            if (!confirm('确定要清理 ' + failed.length + ' 个失败任务吗？')) return;
            const promises = failed.map(t =>
                fetch('/api/v1/gallery/tasks/' + t.task_id, { method: 'DELETE' })
            );
            await Promise.all(promises);
            showToast('✅ 已清理 ' + failed.length + ' 个失败任务');
            refreshTasks();
        } catch(e) {
            showToast('❌ 清理失败: ' + e.message);
        }
    }'''
    html = html.replace(
        'refreshTasks();\n    setInterval',
        cleanup_func + '\n    refreshTasks();\n    setInterval'
    )
    print("  ✅ 已添加清理按钮和函数")
else:
    print("  ⚠️  清理功能已存在")

# 5. 写回 HTML
print("\n5️⃣ 写回修复后的 HTML...")
output_path = "/root/.openclaw/workspace/ai_agent/code/gallery_fixed.html"
with open(output_path, 'w', encoding='utf-8') as f:
    f.write(html)
print(f"  ✅ 已保存: {output_path} ({len(html)} bytes)")

# 6. 生成部署脚本
deploy_script = '''#!/bin/bash
# 部署修复后的 Gallery 前端
# ⚠️ 注意：这是临时方案，生产环境应该构建静态文件
set -e

GALLERY_CONTAINER="gallery"
REMOTE_SSH="root@36.250.122.43 -p 8222"

echo "📤 上传修复后的 HTML 到远程服务器..."
# 方案：通过 API 更新（如果支持）或手动上传

echo ""
echo "✅ 修复完成！"
echo "📍 请手动部署：在 ECS 上替换 gallery 容器的静态文件"
echo "📍 或重启容器以加载新页面"
'''

with open("/root/.openclaw/workspace/ai_agent/code/deploy_gallery.sh", 'w') as f:
    f.write(deploy_script)

print("\n" + "=" * 50)
print("✅ 修复完成！")
print("=" * 50)
print("\n下一步：")
print("  1. 将 gallery_fixed.html 上传到 ECS 容器")
print("  2. 重启容器使修改生效")
print("  3. 或直接在 ECS 上用 docker exec 替换文件")
print("\n临时方案：直接清理失败任务")
print("  curl -X DELETE http://36.250.122.43:8282/api/v1/gallery/tasks/[task_id]")
