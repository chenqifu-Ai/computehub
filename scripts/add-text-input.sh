#!/bin/bash
# Gallery 文字直出功能 — 一键部署
set -euo pipefail

REMOTE="computehub@36.250.122.43"
SRC="/home/computehub/src"

GALLERY_FILE="$SRC/src/gateway/gallery.go"

echo "== 📝 1. 添加 HandleGenerateFromText handler =="
ssh "$REMOTE" "sed -i '/^func (h \*GalleryHandler) HandleTaskStatus/,/^\/\/ runVideoPipeline/{s/^func (h \*GalleryHandler) HandleTaskStatus/\/\/ HandleGenerateFromText 从文字直接生成视频\nfunc (h *GalleryHandler) HandleGenerateFromText(w http.ResponseWriter, r *http.Request) {\n\tif r.Method != http.MethodPost {\n\t\twriteJSON(w, map[string]interface{}{\"success\": false, \"error\": \"Only POST allowed\"})\n\t\treturn\n\t}\n\tbody, _ := io.ReadAll(r.Body)\n\tdefer r.Body.Close()\n\tvar req struct {\n\t\tText     string \`json:\"text\"\`\n\t\tDuration int    \`json:\"duration\"\`\n\t\tBg       string \`json:\"bg\"\`\n\t}\n\tif err := json.Unmarshal(body, \&req); err != nil {\n\t\twriteJSON(w, map[string]interface{}{\"success\": false, \"error\": fmt.Sprintf(\"Invalid JSON: %v\", err)})\n\t\treturn\n\t}\n\tif req.Text == \"\" {\n\t\twriteJSON(w, map[string]interface{}{\"success\": false, \"error\": \"text is required\"})\n\t\treturn\n\t}\n\tif req.Duration <= 0 {\n\t\treq.Duration = 5\n\t}\n\tif req.Bg == \"\" {\n\t\treq.Bg = \"#302b63\"\n\t}\n\ttaskID := fmt.Sprintf(\"text_%d\", time.Now().UnixNano()/1000000)\n\t// 写文本到临时文件\n\ttitle := req.Text\n\tif len([]rune(title)) > 30 {\n\t\ttitle = string([]rune(title)[:30]) + \"...\"\n\t}\n\ttitle = strings.TrimSpace(strings.ReplaceAll(title, \"\\n\", \" \")\n\ttmpDir := \"/tmp/computehub-video/text\"\n\tos.MkdirAll(tmpDir, 0755)\n\ttmpFile := filepath.Join(tmpDir, taskID+\".txt\")\n\tos.WriteFile(tmpFile, []byte(req.Text), 0644)\n\t// 用 temp dir 跑管线\n\th.updateTask(taskID, title, \"pending\", 0, \"文字已提交，正在生成...\")\n\tgo h.runTextPipeline(taskID, tmpFile, title, req.Duration, req.Bg)\n\twriteJSON(w, map[string]interface{}{\n\t\t\"success\": true,\n\t\t\"data\": map[string]interface{}{\n\t\t\t\"task_id\": taskID,\n\t\t\t\"title\":   title,\n\t\t\t\"message\": \"文字已提交，正在生成视频...\",\n\t\t},\n\t})\n}\n\nfunc (h *GalleryHandler) runTextPipeline(taskID, textFile, title string, duration int, bg string) {\n\th.updateTask(taskID, title, \"rendering\", 20, \"正在渲染文字视频...\")\n\tworkerScript := findVideoWorkerScript()\n\tif workerScript == \"\" {\n\t\th.updateTask(taskID, title, \"failed\", 0, \"❌ video_worker.py 未找到\")\n\t\treturn\n\t}\n\tparams := map[string]interface{}{\n\t\t\"task_id\":  taskID,\n\t\t\"doc_path\": textFile,\n\t\t\"title\":    title,\n\t\t\"text_duration\": duration,\n\t\t\"text_bg\": bg,\n\t}\n\tparamsJSON, _ := json.Marshal(params)\n\tos.MkdirAll(\"/tmp/computehub-video/progress\", 0755)\n\tprogressFile := fmt.Sprintf(\"/tmp/computehub-video/progress/%s.json\", taskID)\n\tos.WriteFile(progressFile, []byte(fmt.Sprintf(\n\t\t\`{\"task_id\":\"%s\",\"stage\":\"rendering\",\"percent\":20,\"message\":\"渲染中...\"}\`, taskID)), 0644)\n\tcmd := exec.Command(\"nohup\", \"python3\", workerScript, string(paramsJSON))\n\tlogFile := fmt.Sprintf(\"/tmp/computehub-video/progress/%s_gw.log\", taskID)\n\tlogF, _ := os.Create(logFile)\n\tif logF != nil {\n\t\tcmd.Stdout = logF\n\t\tcmd.Stderr = logF\n\t}\n\tif err := cmd.Start(); err != nil {\n\t\th.updateTask(taskID, title, \"failed\", 0, fmt.Sprintf(\"❌ 启动失败: %v\", err))\n\t\treturn\n\t}\n\tlogWithTimestamp(\"📝 Text Gallery task: task_id=%s text=%s pid=%d\", taskID, textFile, cmd.Process.Pid)\n\tgo func() {\n\t\tcmd.Wait()\n\t\tif logF != nil {\n\t\t\tlogF.Close()\n\t\t}\n\t\t// 检查进度文件\n\t\tif data, readErr := os.ReadFile(progressFile); readErr == nil {\n\t\t\tvar prog map[string]interface{}\n\t\t\tif json.Unmarshal(data, \&prog) == nil {\n\t\t\t\tif output, ok := prog[\"output\"]; ok {\n\t\t\t\t\th.recordToPipelineRepo(taskID, title, textFile, fmt.Sprintf(\"%v\", output))\n\t\t\t\t\th.updateTask(taskID, title, \"completed\", 100, fmt.Sprintf(\"✅ 视频已生成: %v\", output))\n\t\t\t\t\th.refresh()\n\t\t\t\t\tos.Remove(textFile)\n\t\t\t\t\treturn\n\t\t\t\t}\n\t\t\t}\n\t\t}\n\t\th.refresh()\n\t\titems := h.getItems()\n\t\tif len(items) > 0 {\n\t\t\tlatest := items[0]\n\t\t\tif latest.IsVideo {\n\t\t\t\th.recordToPipelineRepo(taskID, title, textFile, latest.Name)\n\t\t\t\th.updateTask(taskID, title, \"completed\", 100, fmt.Sprintf(\"✅ 视频已生成: %s\", latest.Name))\n\t\t\t\tos.Remove(textFile)\n\t\t\t\treturn\n\t\t\t}\n\t\t}\n\t\th.updateTask(taskID, title, \"completed\", 100, \"✅ 处理完成，请刷新作品列表\")\n\t\th.refresh()\n\t\tos.Remove(textFile)\n\t}()\n}\n\nfunc (h *GalleryHandler) HandleTaskStatus/' $GALLERY_FILE"

echo "== 🛣️ 2. 添加路由 =="
ssh "$REMOTE" "sed -i '/http.HandleFunc.*generate.*h.HandleGenerateFromGallery/a\\thttp.HandleFunc(\"/api/v1/gallery/generate-text\", h.HandleGenerateFromText)' $GALLERY_FILE"

ssh "$REMOTE" "sed -i '/generate   → 上传+生成视频/a\\tlogWithTimestamp(\"   - /api/v1/gallery/generate-text → 文字直出视频\")' $GALLERY_FILE"

echo "== 🎨 3. 添加 HTML/JS 文字输入区 =="
# 在 upload-section 和 task-section 之间插入 text-input-section
ssh "$REMOTE" 'python3 << '\''PYEOF'\''
with open("/home/computehub/src/src/gateway/gallery.go", "r") as f:
    content = f.read()

# 找到 task-section 前插入文字输入区
old = """    <!-- ════ 任务进度 ════ -->
    <div class="task-section hidden\""""

new = """    <!-- ════ 文字直出 ════ -->
    <div class="text-input-section">
        <div class="text-input-header">
            <span class="text-input-icon">📝</span>
            <span class="text-input-title">文字直出视频</span>
            <span class="text-input-subtitle">输入文字，每行一个字幕画面，自动转视频</span>
        </div>
        <div class="text-input-area">
            <textarea id="textInput" placeholder="输入你的内容...&#10;&#10;例如：&#10;欢迎来到小智影业&#10;这里是一个全新的世界&#10;用 AI 创造无限可能" rows="5"></textarea>
        </div>
        <div class="text-input-controls">
            <div class="control-group">
                <label>⏱ 每段</label>
                <input type="number" id="durationInput" value="5" min="3" max="20" class="control-input">
                <span class="control-unit">秒</span>
            </div>
            <div class="control-group">
                <label>🎨 背景</label>
                <input type="color" id="bgColor" value="#302b63" class="control-color">
            </div>
            <button class="btn btn-generate" id="btnGenerateText" disabled onclick="generateFromText()">
                🎬 生成视频
            </button>
        </div>
    </div>

    <!-- ════ 任务进度 ════ -->
    <div class="task-section hidden\""""

content = content.replace(old, new)

# 添加 CSS
css_block = """
        .text-input-section {
            margin: 16px 32px;
            background: rgba(255,255,255,0.03);
            border: 1px solid rgba(255,255,255,0.08);
            border-radius: 12px;
            padding: 18px 20px;
        }
        .text-input-header {
            display: flex; align-items: center; gap: 8px; margin-bottom: 12px;
        }
        .text-input-icon { font-size: 20px; }
        .text-input-title { font-size: 15px; font-weight: 600; color: #e0e0e0; }
        .text-input-subtitle { font-size: 12px; color: #666; }
        .text-input-area textarea {
            width: 100%; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 8px; color: #e0e0e0; font-size: 14px; padding: 12px;
            resize: vertical; min-height: 80px; max-height: 300px;
            font-family: inherit; outline: none; transition: border-color 0.2s;
        }
        .text-input-area textarea:focus { border-color: #f7971e; }
        .text-input-area textarea::placeholder { color: #555; }
        .text-input-controls {
            display: flex; align-items: center; gap: 14px; margin-top: 12px; flex-wrap: wrap;
        }
        .control-group {
            display: flex; align-items: center; gap: 6px;
        }
        .control-group label { font-size: 13px; color: #999; }
        .control-input {
            width: 56px; background: rgba(0,0,0,0.3); border: 1px solid rgba(255,255,255,0.1);
            border-radius: 6px; color: #e0e0e0; font-size: 13px; padding: 5px 8px;
            text-align: center; outline: none;
        }
        .control-input:focus { border-color: #f7971e; }
        .control-unit { font-size: 12px; color: #666; }
        .control-color {
            width: 32px; height: 32px; border: 2px solid rgba(255,255,255,0.15);
            border-radius: 6px; cursor: pointer; padding: 0; background: none;
        }
        .control-color::-webkit-color-swatch-wrapper { padding: 0; }
        .control-color::-webkit-color-swatch { border: none; border-radius: 4px; }

        @media (max-width: 768px) {
            .text-input-section { margin: 12px 16px; padding: 14px; }
            .text-input-controls { gap: 10px; }
        }"""

# Insert CSS before .upload-section CSS
old_css = "        .upload-section {"
content = content.replace(old_css, css_block + "\n" + old_css)

with open("/home/computehub/src/src/gateway/gallery.go", "w") as f:
    f.write(content)

print("✅ HTML/CSS 已注入")
PYEOF'

echo "== 🎯 4. 添加 JS 函数 =="
ssh "$REMOTE" 'python3 << '\''PYEOF'\''
with open("/home/computehub/src/src/gateway/gallery.go", "r") as f:
    content = f.read()

# 在 generateVideo() 函数之前或之后插入 generateFromText()
old_js = "    async function generateVideo() {"
new_js = """    // 📝 文字直出 -> 生成视频
    async function generateFromText() {
        const text = document.getElementById('textInput').value.trim();
        if (!text) return;
        const btn = document.getElementById('btnGenerateText');
        btn.disabled = true;
        btn.textContent = '⏳ 提交中...';
        try {
            const r = await fetch('/api/v1/gallery/generate-text', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    text: text,
                    duration: parseInt(document.getElementById('durationInput').value) || 5,
                    bg: document.getElementById('bgColor').value
                })
            });
            const d = await r.json();
            if (d.success) {
                showToast('✅ ' + d.data.message);
                document.getElementById('textInput').value = '';
                btn.disabled = true;
                refreshTasks();
                refreshData();
            } else {
                showToast('❌ ' + (d.error || '生成失败'));
            }
        } catch(e) {
            showToast('❌ 网络错误');
        }
        btn.disabled = false;
        btn.textContent = '🎬 生成视频';
        // 重新评估按钮状态
        checkTextInput();
    }

    // 监听文字输入，启用/禁用按钮
    function checkTextInput() {
        const text = document.getElementById('textInput').value.trim();
        document.getElementById('btnGenerateText').disabled = !text;
    }
    document.addEventListener('DOMContentLoaded', function() {
        const ta = document.getElementById('textInput');
        if (ta) {
            ta.addEventListener('input', checkTextInput);
            checkTextInput();
        }
    });

    async function generateVideo() {"""

content = content.replace(old_js, new_js)

with open("/home/computehub/src/src/gateway/gallery.go", "w") as f:
    f.write(content)

print("✅ JS 已注入")
PYEOF'

echo "== 🐛 5. 修复上一轮 let uploadedFiles 重复声明 =="
# 将第一处 let uploadedFiles 改为 var
ssh "$REMOTE" "sed -i '0,/let uploadedFiles = \[\]/{s/let uploadedFiles = \[\]/var uploadedFiles = []/}' $GALLERY_FILE"

echo "== 🔨 6. 编译 =="
ssh "$REMOTE" "cd $SRC && bash scripts/build_all.sh" 2>&1 | tail -5

echo "== 🚀 7. 部署到 ECS =="
ssh "$REMOTE" "cp $SRC/bin/linux-arm64/computehub /home/computehub/computehub && sudo systemctl restart computehub 2>/dev/null || (pkill -f 'computehub gateway' 2>/dev/null; sleep 1; cd /home/computehub && nohup ./computehub gateway > /dev/null 2>&1 & sleep 2; nohup ./computehub worker --gw http://localhost:8282 --node-id ecs-p2ph --interval 3 --concurrent 8 --heartbeat 10 > /dev/null 2>&1 &)"

echo "== ✅ 8. 验证 =="
sleep 3
ssh "$REMOTE" "curl -s http://localhost:8282/gallery 2>/dev/null | grep -c '文字直出' || echo '⚠️ 未检测到文字直出区'"
ssh "$REMOTE" "ps aux | grep 'computehub gateway' | grep -v grep | head -1"
echo ""
echo "✅ 部署完成！打开 http://36.250.122.43:8282/gallery 查看"
