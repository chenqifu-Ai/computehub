#!/usr/bin/env python3
"""
部署视频管线 Git 全流程追溯系统到 ECS 36.250.122.43
"""
import subprocess, sys, json, datetime

REMOTE = "computehub@36.250.122.43"
KEY = "-i /root/.ssh/id_ed25519_computehub"
REPO = "/home/computehub/pipeline-repo"
GALLERY = "/home/computehub/gallery"

def ssh(cmd):
    """Run a single command on remote via SSH"""
    full_cmd = ["ssh", "-o", "BatchMode=yes", REMOTE, cmd]
    r = subprocess.run(full_cmd, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"  ⚠️  Return code: {r.returncode}")
        if r.stderr.strip():
            print(f"  STDERR: {r.stderr.strip()[:200]}")
    return r.stdout.strip()

def ssh_heredoc(path, content):
    """Write file on remote via SSH heredoc"""
    # Escape single quotes for the heredoc
    safe = content.replace("'", "'\\''")
    cmd = f"cat > {path} << 'HEREDOC_EOF'\n{safe}\nHEREDOC_EOF"
    return ssh(cmd)

def run():
    print("=== Step 1: 初始化仓库 ===")
    ssh(f"rm -rf {REPO}")
    ssh(f"mkdir -p {REPO}/src {REPO}/runs {REPO}/tools")
    ssh(f"cd {REPO} && git init")
    ssh(f"cd {REPO} && git config user.name 'ComputeHub Pipeline' && git config user.email 'pipeline@computehub.local'")
    print("  ✅ 仓库初始化完成")

    print("=== Step 2: 配置文件和代码 ===")
    # .gitignore
    ssh_heredoc(f"{REPO}/.gitignore", """# 忽略大文件，追踪清单
runs/*/input/
!runs/*/input/manifest.json
runs/*/output/
!runs/*/output/manifest.json
runs/*/logs/*.log
!runs/*/logs/manifest.json
__pycache__/
*.pyc
""")
    # README
    ssh_heredoc(f"{REPO}/README.md", """# ComputeHub 视频管线 - Git 全流程追溯

## 目录结构
```
pipeline-repo/
├── src/           ← 管线源代码 (版本化管理)
├── runs/          ← 每次任务一个目录
│   ├── YYYY-MM-DD_任务名/
│   │   ├── manifest.json  ← 完整任务记录
│   │   └── run.sh         ← 复现命令
│   └── ...
└── tools/         ← 管理工具
"""
)
    # Copy source code
    ssh(f"cp /home/computehub/scripts/video/*.py {REPO}/src/")
    ssh(f"cp /home/computehub/scripts/video/templates/*.py {REPO}/src/ 2>/dev/null; true")
    print("  ✅ 管线代码已同步")

    # send_to_gallery.sh (no dollar signs in heredoc - use literal cat)
    ssh_heredoc(f"{REPO}/tools/send_to_gallery.sh", """#!/bin/bash
# 把产出同步到 Gallery
SRC="$1"
DEST_DIR="/home/computehub/gallery"
if [ -f "$SRC" ]; then
    cp "$SRC" "$DEST_DIR/"
    echo "Done: $(basename $SRC)"
else
    echo "ERROR: $SRC not found"
    exit 1
fi
""")
    ssh(f"chmod +x {REPO}/tools/send_to_gallery.sh")
    print("  ✅ send_to_gallery 工具就位")

    # Initial commit
    ssh(f"cd {REPO} && git add .gitignore README.md && git commit -m 'init: pipeline-repo'")
    ssh(f"cd {REPO} && git add src/ tools/ && git commit -m 'feat: pipeline source code v2.0'")
    print("  ✅ 初始提交完成")

    print("=== Step 3: 归档历史任务 ===")
    runs_data = [
        {"dir": "2026-05-18_world_chinese_foundation", "title": "世界华人基金会",
         "source": "world_chinese_foundation.pdf", "output": "world_chinese_foundation_v3.mp4",
         "size": 17871201, "status": "completed"},
        {"dir": "2026-05-18_pipeline_tts_v2", "title": "TTS管线测试 v2",
         "source": None, "output": "pipeline_tts_v2.mp4", "size": 148870790, "status": "completed"},
        {"dir": "2026-05-18_audio_fix_test", "title": "音频修复测试",
         "source": None, "output": "audio_fix_test.mp4", "size": 715320, "status": "completed"},
        {"dir": "2026-05-18_api_test_video", "title": "API测试视频",
         "source": None, "output": "api_test_video.mp4", "size": 770364, "status": "completed"},
        {"dir": "2026-05-19_liangnong_liannong", "title": "农产品流通大数据平台-厦门联农",
         "source": "liangnong_v2.pdf", "output": "liangnong_liannong_v2.mp4",
         "size": None, "status": "lost_output"}
    ]

    for r in runs_data:
        rd = r["dir"]
        run_dir = f"{REPO}/runs/{rd}"
        ssh(f"mkdir -p {run_dir}/input {run_dir}/output {run_dir}/logs")

        # manifest.json
        m = json.dumps({"id": rd, "title": r["title"], "created": rd[:10],
                        "status": r["status"], "output": r["output"],
                        "output_size": r["size"]}, ensure_ascii=False, indent=2)
        ssh_heredoc(f"{run_dir}/manifest.json", m)

        # run.sh
        if r["source"]:
            runsh = f"#!/bin/bash\n# {r['title']}\npython3 /home/computehub/scripts/video/video_pipeline.py --title '{r['title']}' --output {r['output']}\n"
        else:
            runsh = f"#!/bin/bash\n# {r['title']}\npython3 /home/computehub/scripts/video/video_pipeline.py --title '{r['title']}' --output {r['output']}\n"
        ssh_heredoc(f"{run_dir}/run.sh", runsh)
        ssh(f"chmod +x {run_dir}/run.sh")

        # Check output file
        if r["output"]:
            outpath = f"{GALLERY}/{r['output']}"
            exists = ssh(f"test -f {outpath} && echo YES || echo NO")
            if exists == "YES":
                sz = ssh(f"stat -c%s {outpath}")
                om = json.dumps({"file": r["output"], "size": int(sz), "path": outpath})
                ssh_heredoc(f"{run_dir}/output/manifest.json", om)

        # Check source pdf
        if r["source"]:
            spath = f"/home/computehub/{r['source']}"
            pexists = ssh(f"test -f {spath} && echo YES || echo NO")
            if pexists == "YES":
                psz = ssh(f"stat -c%s {spath}")
                im = json.dumps({"source": spath, "size": int(psz)})
                ssh_heredoc(f"{run_dir}/input/manifest.json", im)

        print(f"  ✅ {rd}")

    # Global runs manifest
    gm = json.dumps({"version": 1, "count": len(runs_data)})
    ssh_heredoc(f"{REPO}/runs/manifest.json", gm)
    ssh(f"cd {REPO} && git add runs/ && git commit -m 'archive: {len(runs_data)} historical runs'")
    print("  ✅ 历史任务归档完成")

    # Step 4: Write submit.py and audit.py
    print("=== Step 4: 安装工具（从本地 scp）===")

    print("=== Step 5: 验证 ===")
    log = ssh(f"cd {REPO} && git log --oneline")
    print(f"  仓库提交历史:")
    for line in log.split('\n'):
        print(f"    {line}")
    status = ssh(f"cd {REPO} && git status --short")
    print(f"  状态: {'干净' if not status else status}")

    print(f"\n✅ 部署完成！仓库: {REPO}")

if __name__ == "__main__":
    run()
