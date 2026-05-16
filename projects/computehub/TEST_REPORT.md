╔══════════════════════════════════════════════╗
║  ComputeHub Gateway 功能测试报告              ║
╚══════════════════════════════════════════════╝

📅 测试时间: 2026-05-16 10:59:34
🎯 目标: http://localhost:8282

━━━ 1. 基础 API ━━━
  ✅ Health 端点
  ✅ Status 端点

━━━ 2. Video API ━━━
  ✅ GET /api/v1/video/list
  ✅ POST /api/v1/video/list 拒绝
  ✅ GET /api/v1/video/progress (缺task_id)
  ✅ GET /api/v1/video/progress (无效task)
  ✅ POST /api/v1/video/generate (空body校验)
  ✅ POST /api/v1/video/generate (正确参数)

━━━ 3. 系统状态信息 ━━━
  🖥  节点: 0/0 在线
  📋 任务: 0 活跃 / 0 总计
  ⏱  运行时间: 49m34.084232485s
  ⚙️  调度器: RUNNING (队列深度 0)

━━━ 4. 环境信息 ━━━
  💻 系统: Linux aarch64
  🐍 Python: 3.12.12
  ✅ pip 已安装: edge-tts, Pillow, PyPDF2
  ⚠️  pip 未安装: pydub, moviepy, opencv-python, python-docx, pypdf

━━━ 结果汇总 ━━━
  ✅ 通过: 8/8
  ❌ 失败: 0/8
  📊 通过率: 100%

🎉 全部测试通过!
