#!/usr/bin/env python3
"""Patch gallery.go: change upload flow to upload-then-generate with checkboxes"""
import re

with open("/root/.openclaw/workspace/ai_agent/code/new_gallery.go", "r") as f:
    content = f.read()

# Replace the JS section between "上传" comment and "生成视频" comment
old_start = "    // ══════════════════════════════════════════\n    // 上传\n    // ══════════════════════════════════════════\n    const uploadZone = document.getElementById('uploadZone');"

new_start = """    // ══════════════════════════════════════════
    // 上传（拖入→立刻上传到Gallery）
    // ══════════════════════════════════════════
    let uploadedFiles = [];
    const uploadZone = document.getElementById('uploadZone');"""

assert old_start in content, "old_start not found"
content = content.replace(old_start, new_start, 1)

# Replace handleFileSelect
old_hfs = """    function handleFileSelect(files) {
        for (let f of files) {
            // 去重
            if (pendingFiles.some(p => p.name === f.name && p.size === f.size)) continue;
            pendingFiles.push(f);
        }
        renderFileList();
    }"""

new_hfs = """    function handleFileSelect(files) {
        for (let f of files) {
            uploadToGallery(f);
        }
    }

    async function uploadToGallery(file) {
        const fd = new FormData();
        fd.append('file', file);
        try {
            const r = await fetch('/api/v1/gallery/upload', { method: 'POST', body: fd });
            const d = await r.json();
            if (d.success) {
                const info = d.data;
                uploadedFiles.push({
                    name: info.name,
                    size: info.size,
                    size_str: info.size_str,
                    file_type: info.file_type,
                    role: info.role,
                    checked: true
                });
                renderFileList();
                refreshData();
            } else {
                showToast('❌ ' + file.name + ' 上传失败');
            }
        } catch(e) {
            showToast('❌ ' + file.name + ' 网络错误');
        }
    }

    function toggleFile(index) {
        uploadedFiles[index].checked = !uploadedFiles[index].checked;
        renderFileList();
    }"""

assert old_hfs in content, "old_hfs not found"
content = content.replace(old_hfs, new_hfs, 1)

# Replace removeFile (keep function name but change variable)
old_rf = """    function removeFile(index) {
        pendingFiles.splice(index, 1);
        renderFileList();
    }"""

new_rf = """    function removeFile(index) {
        uploadedFiles.splice(index, 1);
        renderFileList();
    }"""

assert old_rf in content, "old_rf not found"
content = content.replace(old_rf, new_rf, 1)

# Replace clearFiles
old_cf = """    function clearFiles() {
        pendingFiles = [];
        renderFileList();
    }"""

new_cf = """    function clearFiles() {
        uploadedFiles = [];
        renderFileList();
    }"""

assert old_cf in content, "old_cf not found"
content = content.replace(old_cf, new_cf, 1)

# Replace renderFileList
old_rfl = """    function renderFileList() {
        const container = document.getElementById('fileList');
        const itemsDiv = document.getElementById('fileItems');
        const countSpan = document.getElementById('fileCount');
        const btn = document.getElementById('btnGenerate');

        if (pendingFiles.length === 0) {
            container.classList.add('hidden');
            btn.disabled = true;
            return;
        }

        container.classList.remove('hidden');
        btn.disabled = false;
        countSpan.textContent = '已选 ' + pendingFiles.length + ' 个文件';

        let html = '';
        pendingFiles.forEach((f, i) => {
            const info = classifyFile(f.name);
            html += '<div class="file-item">' +
                '<span class="icon">' + info.label.charAt(0) + '</span>' +
                '<span class="name" title="'+f.name+'">' + escapeHtml(f.name) + '</span>' +
                '<span class="size">' + formatSize(f.size) + '</span>' +
                '<span class="badge ' + info.badge + '">' + info.label + '</span>' +
                '<span class="badge badge-success">✅</span>' +
                '<button onclick="removeFile('+i+')" style="background:none;border:none;color:#ef5350;cursor:pointer;font-size:14px;">✕</button>' +
                '</div>';
        });
        itemsDiv.innerHTML = html;
    }"""

new_rfl = """    function renderFileList() {
        const container = document.getElementById('fileList');
        const itemsDiv = document.getElementById('fileItems');
        const countSpan = document.getElementById('fileCount');
        const btn = document.getElementById('btnGenerate');

        if (uploadedFiles.length === 0) {
            container.classList.add('hidden');
            btn.disabled = true;
            return;
        }

        container.classList.remove('hidden');
        const checked = uploadedFiles.filter(f => f.checked).length;
        btn.disabled = checked === 0;
        countSpan.textContent = '已上传 ' + uploadedFiles.length + ' 个，勾选 ' + checked + ' 个';

        let html = '';
        uploadedFiles.forEach((f, i) => {
            const info = classifyFile(f.name);
            html += '<div class="file-item">' +
                '<input type="checkbox" ' + (f.checked ? 'checked' : '') +
                ' onchange="toggleFile('+i+')" style="width:16px;height:16px;accent-color:#f7971e;cursor:pointer;">' +
                '<span class="icon">' + info.label.charAt(0) + '</span>' +
                '<span class="name" title="'+f.name+'">' + escapeHtml(f.name) + '</span>' +
                '<span class="size">' + f.size_str + '</span>' +
                '<span class="badge ' + info.badge + '">' + info.label + '</span>' +
                '<span class="badge badge-success">✅</span>' +
                '<button onclick="removeFile('+i+')" style="background:none;border:none;color:#ef5350;cursor:pointer;font-size:14px;">✕</button>' +
                '</div>';
        });
        itemsDiv.innerHTML = html;
    }"""

if old_rfl not in content:
    # Try alternative - exact copy from file
    print("ERROR: old_rfl not found")
    print("Last 500 chars of section:")
    idx = content.find("function renderFileList")
    print(content[idx:idx+700])
else:
    content = content.replace(old_rfl, new_rfl, 1)

# Replace generateVideo
old_gv = """    async function generateVideo() {
        if (pendingFiles.length === 0) return;

        const btn = document.getElementById('btnGenerate');
        btn.disabled = true;
        btn.textContent = '⏳ 提交中...';

        const formData = new FormData();
        for (let f of pendingFiles) {
            formData.append('files[]', f);
        }

        try {
            const r = await fetch('/api/v1/gallery/generate', {
                method: 'POST',
                body: formData
            });
            const d = await r.json();

            if (d.success) {
                showToast('✅ ' + d.data.message);
                // 清空文件列表
                pendingFiles = [];
                renderFileList();
                // 立即刷新任务
                refreshTasks();
                // 刷新作品列表
                refreshData();
            } else {
                showToast('❌ ' + (d.error || '生成失败'));
            }
        } catch(e) {
            showToast('❌ 网络错误');
        }"""

new_gv = """    async function generateVideo() {
        const checked = uploadedFiles.filter(f => f.checked);
        if (checked.length === 0) return;

        const btn = document.getElementById('btnGenerate');
        btn.disabled = true;
        btn.textContent = '⏳ 提交中...';

        try {
            const r = await fetch('/api/v1/gallery/generate', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ filenames: checked.map(f => f.name) })
            });
            const d = await r.json();

            if (d.success) {
                showToast('✅ ' + d.data.message);
                uploadedFiles = [];
                renderFileList();
                refreshTasks();
                refreshData();
            } else {
                showToast('❌ ' + (d.error || '生成失败'));
            }
        } catch(e) {
            showToast('❌ 网络错误');
        }"""

if old_gv not in content:
    print("ERROR: old_gv not found")
    idx = content.find("async function generateVideo")
    print(content[idx:idx+700])
else:
    content = content.replace(old_gv, new_gv, 1)

with open("/root/.openclaw/workspace/ai_agent/code/new_gallery.go", "w") as f:
    f.write(content)

print("Patched successfully!")
