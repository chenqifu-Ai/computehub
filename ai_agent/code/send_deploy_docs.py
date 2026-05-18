#!/usr/bin/env python3
"""发送 deploy.sh 详解到邮箱"""
import smtplib
from email.mime.text import MIMEText
from email.header import Header
import sys

# ⚠️ 请替换为你的 QQ 邮箱 SMTP 授权码
# QQ 邮箱 → 设置 → 帐户 → 开启 SMTP → 生成授权码
SMTP_USER = "19525456@qq.com"
SMTP_PASS = "你的QQ邮箱SMTP授权码"  # 不是QQ密码！

TO = "19525456@qq.com"

body = """
Hi 老大，

以下是 deploy.sh 脚本的全量详解，按部分拆开讲。

========================================
ComputeHub deploy.sh 脚本详解
========================================

一、概述
───────────────────────────────────────

deploy.sh 是 ComputeHub 部署的统一入口，覆盖 5 个功能：

  1. 编译 (build)    — 全平台交叉编译（linux/darwin/windows × amd64/arm64）
  2. 同步 (sync)     — 编译产物分发到 deploy/ 目录 + 生成 sha256 校验
  3. 推送 (push)     — SSH 传输二进制到远程机器 + 安装 + 启动服务
  4. 部署 (deploy)   — build + push 合体，一行搞定
  5. 升级 (upgrade)  — 通过 Gateway API 远程升级 Worker

用法一览：

  bash scripts/deploy.sh build [version]              # 编译
  bash scripts/deploy.sh deploy <host> [args]         # build + 推送
  bash scripts/deploy.sh push <host> [args]           # 仅推送
  bash scripts/deploy.sh upgrade [node_id]            # 远程升级
  bash scripts/deploy.sh sync                         # 同步到 deploy/


二、基础设置
───────────────────────────────────────

  set -euo pipefail

  -e      → 脚本中任何命令失败就退出（不继续往下跑）
  -u      → 使用了未定义的变量就报错
  -o pipefail → 管道中任意一段失败就算整体失败

  cd "$(dirname "$0")/.."    → 定位到项目根目录
  PROJECT_DIR=$(pwd)         → 项目根
  BIN_DIR=…/bin              → 编译产物存放
  DEPLOY_DIR=…/deploy        → 分发目录（用于推送）

为什么要从脚本目录向上跳一层？
因为脚本可能在 scripts/deploy.sh，也可以从项目根用相对路径调，需要统一锚点。


三、工具函数
───────────────────────────────────────

  1. get_version()
     从 src/version/version.go 提取 VERSION 字符串。
     版本号只定义在源码里，脚本自动读取，不会不一致。

  2. get_platform()
     调 uname 检测本机 OS 和架构 → 输出 "linux-arm64" 等。
     用于 deploy/ 根目录放一份当前平台二进制，方便本地测试。

  3. find_binary(platform)
     依次检查三个目录是否有指定平台的二进制：
       bin/ → deploy/{version}/ → deploy/
     优先用编译产物，不行就 fallback 到归档版本。

  4. detect_remote_arch(ssh_cmd)
     通过 SSH 执行远程 uname -m，返回远程架构。
     SSH 命令由调用方传入（密钥还是密码，由外层决定）。


四、cmd_build — 编译（核心）
───────────────────────────────────────

  1. 检查 go 是否安装，没装直接退出
  
  2. ldflags 设置：
       -s       → strip 符号表（瘦身 ~4MB）
       -w       → 去掉 DWARF 调试信息（再瘦身）
       -X …BUILD=$(date +%s) → 注入编译时间戳

  3. 遍历 5 个平台交叉编译：
       linux/amd64  → linux-amd64（云服务器主力）
       linux/arm64  → linux-arm64（ARM 服务器 / 树莓派）
       darwin/amd64 → darwin-amd64（Intel Mac）
       darwin/arm64 → darwin-arm64（Apple Silicon Mac）
       windows/amd64 → windows-amd64（Windows 机器）

  4. 关键编译参数：
       CGO_ENABLED=0  → 纯静态编译，不依赖 C 库，跨平台直接跑
       先编到 .tmp 文件 → 成功才 mv，防止中断留垃圾

  5. 编译完成后自动调用 cmd_sync 同步到 deploy/


五、cmd_sync — 同步
───────────────────────────────────────

  把 bin/ 下各平台的二进制平铺到 deploy/ 目录：

    deploy/linux-arm64/computehub
    deploy/linux-amd64/computehub
    deploy/darwin-amd64/computehub
    …

  同时生成：
    sha256sums-{version}.txt  → 所有二进制的校验和
    version.txt               → 当前版本号

  设计意图：
    bin/ 是编译车间（按版本累积，可追溯）
    deploy/ 是货架（永远是最新可用版本，推送时从这里拿）


六、cmd_push — 推送（最复杂的部分）
───────────────────────────────────────

  参数解析（支持）：

    -u/--user      SSH 用户名         默认 computehub
    -p/--password  SSH 密码           有密码用 sshpass，无密码用密钥
    -P/--port      SSH 端口           默认 22
    -a/--action    推送后动作          restart/gateway/worker/none
    --gateway      Gateway URL        默认 http://{host}:8282
    --node-id      Worker 节点 ID     默认 hostname-worker

  SSH 连接策略：

    有密码 → 用 sshpass 自动输密码（手机 Termux 场景）
    无密码 → 用 SSH 密钥（云服务器场景）
    最终拼装成 SSH_CMD="eval ssh ... user@host"
    这种方式让后续所有 SSH 操作统一走同一个命令字符串

  传输流程（6 步）：

    [1] 连接检测
        $SSH_CMD "uname -a" → 确认对方在线且 SSH 正常

    [2] 架构检测
        detect_remote_arch → 决定推送哪个平台的二进制
        自动识别 ARM 还是 x86，推错就跑不了

    [3] SCP 传输
        先传到 ~/computehub-v{version}（带版本号的存档副本）
        再 cp 为 ~/computehub（始终是最新版的别名）
        既有历史可回溯，又有"最新版"方便引用

    [4] 大小验证
        对比本地和远程文件大小，不一致就报警
        网络中断或 SCP 异常时能发现

    [5] 安装到 PATH
        普通 Linux → /usr/local/bin/computehub
        Termux     → $PREFIX/bin/computehub
        安装后执行 version 命令验证可执行

    [6] 执行动作（-a 参数）

        restart:  pkill 杀所有 → 启动 gateway → 启动 worker
        gateway:  pkill 杀 gateway → 单独启动 gateway
        worker:   pkill 杀 worker → 单独启动 worker
        none:     只传文件，不启动

    启动方式：nohup ... & 后台运行，日志写 /tmp/
    健康检查：gateway 用 curl 测端口，worker 用 pgrep 查进程


七、cmd_deploy — 部署（build + push 合并）
───────────────────────────────────────

  就是一个快捷方式，先 build 再 push：

    cmd_build
    cmd_push "$host" "$@"

  一行命令搞定编译到部署的全流程，适合 CI/CD 流水线。


八、cmd_upgrade — 远程升级
───────────────────────────────────────

  通过 Gateway API（默认 http://localhost:8282）给 Worker 发升级任务。
  不指定节点 ID 就升级所有在线节点。
  实际调用 upgrade.sh 脚本执行 HTTP 交互。

  设计理念：不需要 SSH 也能升级 Worker，Gateway 作为管控中心。


九、设计思想总结
───────────────────────────────────────

  1. 版本号一处定义
     从 Go 源码读，不重复配置，避免手写版本不一致

  2. 三处找二进制（bin/ → 归档 → 当前版）
     容错性好，不管从哪步开始都能找到可用产物

  3. temp 文件 + rename
     编译中断不污染输出，不会留下半截二进制

  4. 密钥优先 + 密码兜底
     云服务器用密钥安全快速，手机 Termux 用密码兼容

  5. 版本存档 + 最新别名
     既有历史可回溯，又有"最新版"方便引用

  6. 纯静态编译 + strip
     跨平台，体积从 13MB 瘦到 9MB，传输更快

  7. 全流程覆盖
     代码 → 编译 → 传输 → 安装 → 启动 → 验证
     一个脚本解决全部部署需求

  8. 统一入口
     不管目标机器是阿里云 ECS、树莓派还是 Android 手机，
     同一个脚本，不同参数搞定。

========================================

— 小智
"""

def send():
    msg = MIMEText(body, "plain", "utf-8")
    msg["Subject"] = Header("ComputeHub deploy.sh 脚本详解", "utf-8")
    msg["From"] = SMTP_USER
    msg["To"] = TO

    try:
        s = smtplib.SMTP_SSL("smtp.qq.com", 465, timeout=10)
        s.login(SMTP_USER, SMTP_PASS)
        s.sendmail(SMTP_USER, [TO], msg.as_string())
        s.quit()
        print("✅ 邮件发送成功")
    except Exception as e:
        print(f"❌ 发送失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    send()
