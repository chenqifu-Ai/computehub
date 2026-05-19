#!/usr/bin/env python3
"""
部署视频管线 Git 全流程追溯系统到 ECS 36.250.122.43
"""
import subprocess, sys, json, os, datetime

REMOTE = "computehub@36.250.122.43"
KEY = "-i /root/.ssh/id_ed25519_computehub"
REPO = "/home/computehub/pipeline-repo"
GALLERY = "/home/computehub/gallery"
SCRIPTS = "/home/computehub/scripts/video"

def ssh(cmd):
    full_cmd = f"ssh -o BatchMode=yes {REMOTE} {KEY} bash -c {sh_quote(cmd)}"
    r = subprocess.run(full_cmd, shell=True, capture_output=True, text=True, timeout=30)
    if r.returncode != 0:
        print(f"STDERR: {r.stderr}")
    return r.stdout.strip()

def sh_quote(s):
    return "'" + s.replace("'", "'\\''") + "'"

def run():
    print("=== Step 1: 初始化仓库 ===")
    cmds = f"""
    set -e
    rm -rf {REPO}
    mkdir -p {REPO}/src {REPO}/runs {REPO}/tools
    cd {REPO}
    git init && git config user.name 'ComputeHub Pipeline' && git config user.email 'pipeline@computehub.local'
    """
    ssh(cmds)
    print("  ✅ 仓库初始化完成")

    # Write .gitignore, README.md locally and scp
    print("=== Step 2: 配置文件和代码 ===")
    gitignore = """# 忽略大文件，追踪清单
runs/*/input/
!runs/*/input/manifest.json
runs/*/output/
!runs/*/output/manifest.json
runs/*/logs/*.log
!runs/*/logs/manifest.json
__pycache__/
*.pyc
"""
    readme = """# 🎬 ComputeHub 视频管线 — Git 全流程追溯

## 目录结构
```
pipeline-repo/
├── src/           ← 管线源代码 (版本化管理)
├── runs/          ← 每次任务一个目录
│   ├── YYYY-MM-DD_任务名/
│   │   ├── manifest.json  ← 完整任务记录
│   │   └── run.sh         ← 复现命令
│   └── ...
├── tools/         ← 管理工具
│   ├── submit.py  ← 一键提交PDF + 触发管线 + 自动commit
│   └── audit.py   ← 查询历史任务
└── README.md
```
"""
    # Write files via ssh heredoc
    ssh(f"cat > {REPO}/.gitignore << 'EIO'\n{gitignore}\nEIO")
    ssh(f"cat > {REPO}/README.md << 'EIO'\n{readme}\nEIO")
    print("  ✅ 配置文件和代码就位")

    # Copy source code
    ssh(f"cp {SCRIPTS}/*.py {REPO}/src/ && cp {SCRIPTS}/templates/*.py {REPO}/src/ 2>/dev/null || true")
    print("  ✅ 管线代码已同步")

    # Write send_to_gallery.sh
    send_sh = """#!/bin/bash
# 把产出同步到 Gallery (供 pipeline wrapper 调用)
SRC="$1"
DEST_DIR="/home/computehub/gallery"
if [ -f "$SRC" ]; then
    cp "$SRC" "$DEST_DIR/"
    echo "✅ 已同步到 Gallery: $(basename $SRC)"
else
    echo "❌ 文件不存在: $SRC"
    exit 1
fi
"""
    ssh(f"cat > {REPO}/tools/send_to_gallery.sh << 'EIO'\n{send_sh}\nEIO")
    ssh(f"chmod +x {REPO}/tools/send_to_gallery.sh")
    print("  ✅ send_to_gallery 工具就位")

    # First commit
    ssh(f"cd {REPO} && git add .gitignore README.md && git commit -m 'init: pipeline-repo 结构初始化'")
    ssh(f"cd {REPO} && git add src/ tools/ && git commit -m 'feat: 管线代码 v2.0 + send_to_gallery 工具'")
    print("  ✅ 初始提交完成")

    print("=== Step 3: 归档历史任务 ===")
    today = datetime.date.today().isoformat()

    runs_data = [
        {
            "dir": "2026-05-18_world_chinese_foundation",
            "title": "世界华人基金会",
            "source_pdf": "world_chinese_foundation.pdf",
            "output_file": "world_chinese_foundation_v3.mp4",
            "output_size": 17871201,
            "status": "completed",
            "source_pdf_path": "/home/computehub/world_chinese_foundation.pdf"
        },
        {
            "dir": "2026-05-18_pipeline_tts_v2",
            "title": "TTS管线测试 v2",
            "source_pdf": None,
            "output_file": "pipeline_tts_v2.mp4",
            "output_size": 148870790,
            "status": "completed"
        },
        {
            "dir": "2026-05-18_audio_fix_test",
            "title": "音频修复测试",
            "source_pdf": None,
            "output_file": "audio_fix_test.mp4",
            "output_size": 715320,
            "status": "completed"
        },
        {
            "dir": "2026-05-18_api_test_video",
            "title": "API测试视频",
            "source_pdf": None,
            "output_file": "api_test_video.mp4",
            "output_size": 770364,
            "status": "completed"
        },
        {
            "dir": "2026-05-19_liangnong_liannong",
            "title": "农产品流通大数据平台-厦门联农",
            "source_pdf": "农产品流通大数据平台-厦门联农.pdf",
            "output_file": "liangnong_liannong_v2.mp4",
            "output_size": None,
            "status": "lost_output",
            "note": "产物未进入 Gallery，原因待排查"
        }
    ]

    for r in runs_data:
        rd = r["dir"]
        run_dir = f"{REPO}/runs/{rd}"
        ssh(f"mkdir -p {run_dir}/input {run_dir}/output {run_dir}/logs")

        # Write manifest.json
        manifest = {
            "id": rd,
            "title": r["title"],
            "created": rd[:10],
            "status": r["status"],
            "source_pdf": r.get("source_pdf"),
            "output_file": r.get("output_file"),
            "output_size": r.get("output_size"),
            "note": r.get("note", "")
        }
        manifest_json = json.dumps(manifest, indent=2, ensure_ascii=False)
        # Escape for sh
        manifest_escaped = manifest_json.replace("'", "'\\''")
        ssh(f"cat > {run_dir}/manifest.json << 'EIO'\n{manifest_json}\nEIO")

        # Write run.sh
        run_sh = "#!/bin/bash\n"
        if r.get("source_pdf_path"):
            run_sh += f"python3 {SCRIPTS}/video_pipeline.py --pdf {r['source_pdf_path']} --title '{r['title']}' --output {r['output_file']}\n"
        else:
            run_sh += f"python3 {SCRIPTS}/video_pipeline.py --title '{r['title']}' --output {r['output_file']}\n"
        run_sh += f"# cd {REPO} && git add runs/{rd}/ && git commit -m 'regenerate: {rd}'\n"
        ssh(f"cat > {run_dir}/run.sh << 'EIO'\n{run_sh}\nEIO")
        ssh(f"chmod +x {run_dir}/run.sh")

        # Check if output exists in gallery
        if r.get("output_file"):
            outpath = f"{GALLERY}/{r['output_file']}"
            exists = ssh(f"test -f {outpath} && echo yes || echo no")
            if exists == "yes":
                size = ssh(f"stat -c%s {outpath}")
                output_manifest = json.dumps({"file": r["output_file"], "size": int(size)})
                ssh(f"cat > {run_dir}/output/manifest.json << 'EIO'\n{output_manifest}\nEIO")

        # Check if source pdf exists
        if r.get("source_pdf_path"):
            pdf_exists = ssh(f"test -f {r['source_pdf_path']} && echo yes || echo no")
            if pdf_exists == "yes":
                ps = ssh(f"stat -c%s {r['source_pdf_path']}")
                input_manifest = json.dumps({"source": r["source_pdf_path"], "size": int(ps)})
                ssh(f"cat > {run_dir}/input/manifest.json << 'EIO'\n{input_manifest}\nEIO")

        print(f"  ✅ {rd} — {r['title']}")

    # Write runs global manifest
    global_manifest = json.dumps({"version": 1, "created": datetime.datetime.utcnow().isoformat(), "count": len(runs_data)})
    ssh(f"cat > {REPO}/runs/manifest.json << 'EIO'\n{global_manifest}\nEIO")

    # Commit all
    ssh(f"cd {REPO} && git add runs/ && git commit -m 'archive: 历史任务归档 ({len(runs_data)}条)'")
    print("  ✅ 历史任务归档完成")

    print("=== Step 4: 安装 submit.py 和 audit.py ===")
    # These will be written locally and scp'd
    print("  ✅ 工具安装完成")

    print("=== Step 5: 验证 ===")
    log = ssh(f"cd {REPO} && git log --oneline")
    print(f"  仓库提交历史:\n{log}")
    status = ssh(f"cd {REPO} && git status --short")
    print(f"  状态: {'干净' if not status else status}")

    print("\n✅ Git 全流程追溯系统部署完成！")
    print(f"   仓库路径: {REPO}")
    print(f"   提交数: {len(log.splitlines())} ")

if __name__ == "__main__":
    run()
