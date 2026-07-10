#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import os, subprocess
d = "/home/ubuntu/.openclaw/agents/main"
os.makedirs(d + "/agent", exist_ok=True)
files = {
    d + "/SOUL.md": "# SOUL.md\n\n名称: 小乌 (wanlida-ubuntu)\n节点: Ubuntu 24.04, x86_64, 15GB RAM\n上色: 集群计算节点\n",
    d + "/USER.md": "# USER.md\n识乐: 老大\n时区: Asia/Shanghai\n",
    d + "/AGENTS.md": "# AGENTS.md\n\n我是小乌，wanlida-ubuntu 上的 OpenClaw Agent\n",
    d + "/BOOTSTRAP.md": "# BOOTSTRAP.md\n\n（天次，请取操作同旣向回复上线\n",
    d + "/agent/config.json": '{"model":"zhangtuo-ai-main/qwen3.6-35b"}\n',
}
for path, content in files.items():
    with open(path, "w") as f:
        f.write(content)
    print("OK", path)
subprocess.run(["chown", "-R", "ubuntu:ubuntu", d], capture_output=True)
print("DONE")
