#!/usr/bin/env python3
"""
⚙️ ComputeHub Video Worker — Worker 内置模块

Worker 通过此脚本接收 JSON 参数并执行视频生成流水线。
不需要通过 API 传输代码（修复 #8），只传参数。

用法（Worker 调用）:
  python3 video_worker.py '{
    "task_id": "v1234",
    "doc_path": "/path/file.pptx",
    "template": "business",
    "voice": "yunxi",
    "page_duration": 5
  }'

Worker 提交:
  1. 接收 HTTP POST /api/v1/video/generate
  2. 解析参数 JSON
  3. nohup 后台执行 video_worker.py（修复 #9）
  4. 立即返回 task_id 给客户端
  5. 客户端通过 /api/v1/video/{task_id}/progress 轮询进度
"""
import json
import os
import subprocess
import sys
import time
import traceback
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.absolute()
PIPELINE = os.path.join(SCRIPT_DIR, "video_pipeline.py")

PROGRESS_DIR = "/tmp/computehub-video/progress"


def submit(params: dict) -> dict:
    """提交视频生成任务（后台执行）

    修复 #9: nohup 后台执行，永不超时
    """
    task_id = params.get("task_id") or f"video_{int(time.time())}"

    # 构建 CLI 参数
    cmd = [sys.executable, PIPELINE]

    doc_path = params.get("doc_path") or params.get("doc")
    if not doc_path:
        return {"success": False, "error": "doc_path required", "task_id": task_id}
    cmd.extend(["--doc", doc_path])

    if params.get("output"):
        cmd.extend(["--output", params["output"]])
    if params.get("template"):
        cmd.extend(["--template", params["template"]])
    if params.get("voice"):
        cmd.extend(["--voice", params["voice"]])
    if params.get("page_duration"):
        cmd.extend(["--page-duration", str(params["page_duration"])])
    if params.get("no_tts") or params.get("no-tts"):
        cmd.append("--no-tts")

    cmd.extend(["--task-id", task_id, "--progress"])

    log_file = os.path.join(PROGRESS_DIR, f"{task_id}_worker.log")
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    # nohup 后台执行
    nohup_cmd = f'nohup {" ".join(cmd)} > {log_file} 2>&1 &'
    print(f"  🚀 提交任务 [{task_id}]: {nohup_cmd[:200]}...")

    subprocess.Popen(
        ["nohup", sys.executable, PIPELINE] + cmd[2:] + ["--progress"],
        stdout=open(log_file, "w"),
        stderr=subprocess.STDOUT,
    )

    return {
        "success": True,
        "task_id": task_id,
        "message": "任务已提交后台执行",
    }


def query_progress(task_id: str) -> dict:
    """查询任务进度"""
    progress_file = os.path.join(PROGRESS_DIR, f"{task_id}.json")
    log_file = os.path.join(PROGRESS_DIR, f"{task_id}_worker.log")

    if os.path.exists(progress_file):
        with open(progress_file) as f:
            return json.load(f)

    # 没有进度文件，检查日志
    if os.path.exists(log_file):
        # 读取最后几行看有没有 PROGRESS_JSON
        with open(log_file) as f:
            lines = f.readlines()
        for line in reversed(lines[-20:]):
            if "PROGRESS_JSON:" in line:
                try:
                    json_str = line.split("PROGRESS_JSON:", 1)[1].strip()
                    return json.loads(json_str)
                except Exception:
                    pass

        # 检查是否还在运行
        running = check_process_running(task_id)
        return {
            "task_id": task_id,
            "stage": "running" if running else "unknown",
            "percent": -1,
            "message": "处理中..." if running else "状态未知",
        }

    return {
        "task_id": task_id,
        "stage": "not_found",
        "percent": 0,
        "message": "任务未找到",
    }


def check_process_running(task_id: str) -> bool:
    """检查 video_worker 进程是否还在运行（通过 ps grep）"""
    import subprocess
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True, text=True, timeout=5,
        )
        return task_id in result.stdout
    except Exception:
        return False


# ── CLI 入口 ──────────────────────────────────────────────────

def main():
    if len(sys.argv) < 2:
        print("用法: python3 video_worker.py <json_params>")
        print("  或: python3 video_worker.py --progress <task_id>")
        sys.exit(1)

    if sys.argv[1] == "--progress":
        # 查询进度
        task_id = sys.argv[2] if len(sys.argv) > 2 else input("task_id: ")
        result = query_progress(task_id)
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif sys.argv[1] == "--list":
        # 列出所有任务
        if os.path.exists(PROGRESS_DIR):
            tasks = []
            for f in sorted(os.listdir(PROGRESS_DIR)):
                if f.endswith(".json") and not f.endswith("_worker.log.json"):
                    task_id = f[:-5]
                    with open(os.path.join(PROGRESS_DIR, f)) as pf:
                        try:
                            data = json.load(pf)
                            tasks.append({
                                "task_id": task_id,
                                "stage": data.get("stage", "?"),
                                "percent": data.get("percent", 0),
                                "message": data.get("message", ""),
                            })
                        except Exception:
                            pass
            print(json.dumps(tasks, ensure_ascii=False, indent=2))
        else:
            print("[]")
    else:
        # 提交任务
        try:
            params = json.loads(sys.argv[1])
        except json.JSONDecodeError as e:
            # 可能是未引号的字符串，尝试作为 doc_path
            params = {"doc_path": sys.argv[1]}

        result = submit(params)
        print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
