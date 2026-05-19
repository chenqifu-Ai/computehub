#!/usr/bin/env python3
"""STD-002 Git 提交脚本 — Gateway node 字段兼容改动"""

import subprocess
import sys
import os

WORKSPACE = "/root/.openclaw/workspace"

def run(cmd: str, cwd: str = WORKSPACE) -> subprocess.CompletedProcess:
    print(f"➜ {cmd}")
    result = subprocess.run(
        cmd, shell=True, cwd=cwd,
        capture_output=True, text=True
    )
    if result.stdout:
        print(result.stdout)
    if result.stderr:
        print(result.stderr, file=sys.stderr)
    return result

def main():
    print("=" * 60)
    print("📝 Git 提交 — STD-002: Gateway node 字段兼容")
    print("=" * 60)

    # 1. 智能分析：查看当前状态
    print("\n【1/5】检查当前 Git 状态")
    status = run("git status --short")
    if not status.stdout.strip():
        print("✅ 无变更需要提交")
        return

    # 显示变更文件列表
    print("\n变更文件:")
    for line in status.stdout.strip().splitlines():
        print(f"  {line}")

    # 2. 代码生成：准备提交
    print("\n【2/5】添加变更文件")
    result = run("git add -A")
    if result.returncode != 0:
        print("❌ 添加文件失败")
        sys.exit(1)

    # 3. 确认提交内容
    print("\n【3/5】查看提交预览")
    staged = run("git diff --cached --stat")
    if staged.stdout.strip():
        print(f"  预计变更: {staged.stdout.strip()}")
    else:
        print("  ⚠️ 无暂存变更")

    # 4. 执行提交
    print("\n【4/5】执行提交")
    commit_msg = "feat(gateway): 支持 node 字段兼容 (STD-002)\n\n- TaskSubmit 添加 node 字段，兼容旧版客户端\n- 映射逻辑: node > node_id > assigned_node 优先级\n- 三种写法均可正确定向调度到指定节点\n- 文档: memory/topics/执行规则/STD-002_Gateway任务调度node字段兼容.md"
    result = run(f'git commit -m "{commit_msg}"')
    if result.returncode != 0:
        print("❌ 提交失败")
        sys.exit(1)
    print("✅ 提交成功")

    # 5. 验证结果
    print("\n【5/5】验证提交")
    log_result = run("git log -1 --oneline")
    push_result = run("git push 2>&1 || echo '⚠️ Push skipped (可能无远程仓库或无权限)'")

    print("\n" + "=" * 60)
    print("✅ 提交完成")
    print(f"📋 提交信息: {commit_msg.split(chr(10))[0]}")
    print("=" * 60)

if __name__ == "__main__":
    main()
