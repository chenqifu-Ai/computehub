# deploy.sh 流程图

```mermaid
flowchart TD
    START([运行 deploy.sh]) --> PARSE{子命令?}
    
    PARSE -->|build [ver]| BUILD[cmd_build]
    PARSE -->|deploy| DEPLOY[cmd_deploy]
    PARSE -->|all| ALL[先 build 后 deploy]

    %% ===== build 流程 =====
    BUILD --> B_GO{go version?}
    B_GO -->|失败| B_ERR[err: Go not found → exit 1]
    B_GO -->|成功| B_LOOP[遍历 linux-amd64 / linux-arm64 / windows-amd64]
    B_LOOP --> B_COMP[遍历 gateway/tui/worker/node]
    B_COMP --> B_SRC{源目录存在?}
    B_SRC -->|否| B_SKIP[warn 跳过]
    B_SRC -->|是| B_COMPILE[CGO_ENABLED=0 GOOS/GOARCH ➔ go build]
    B_COMPILE --> B_COMP
    B_COMP --> B_NEXT[下一个平台]
    B_NEXT --> B_SYNC[sync_deploy: 复制 bin/ ➔ deploy/ + sha256sums]
    B_SYNC --> B_DONE[ok: build done]

    %% ===== deploy 流程 =====
    DEPLOY --> D_INIT[解析参数: host, password, --component, --port, --gateway, --user...]
    D_INIT --> D_GW_URL{gw 有 http://?}
    D_GW_URL -->|无| D_GW_FIX[自动补 http://]
    D_GW_URL -->|有| D_PING

    D_PING --> D_CHECK{ping 通?}
    D_CHECK -->|通| D_SSH
    D_CHECK -->|不通| D_NC{nc -z host:port?}
    D_NC -->|不通| D_ERR[err: unreachable ➔ exit 1]
    D_NC -->|通| D_SSH

    D_SSH --> D_SSH_OK{ssh_exec uname -a OK?}
    D_SSH_OK -->|失败| D_SSH_ERR[err: SSH failed ➔ exit 1]
    D_SSH_OK -->|成功| D_PLATFORM[ssh: uname -s 拿 os, uname -m 拿 arch]

    D_PLATFORM --> D_PLATFORM_DECIDE{arch?}
    D_PLATFORM_DECIDE -->|aarch64 / arm64| D_PLATFORM_ARM[platform = linux-arm64]
    D_PLATFORM_DECIDE -->|x86_64 / amd64| D_PLATFORM_AMD[platform = linux-amd64]
    D_PLATFORM_DECIDE -->|其他| D_PLATFORM_FALLBACK[warn ➔ 尝试 linux-amd64]

    D_PLATFORM_ARM --> D_COMPS[解析组件列表]
    D_PLATFORM_AMD --> D_COMPS

    D_COMPS --> D_LOOP[遍历每个组件]
    D_LOOP --> D_DOWNLOAD[download_via_gateway]
    
    subgraph download_via_gateway
        DG_START([传入 host/pass/port/user/comp/platform/gw])
        DG_URL[拼接下载 URL: gw/api/v1/download?file=computehub-{comp}-{platform}.ext]
        DG_SSH[ssh ➔ curl -sL -o 下载到远程 ~/]
        DG_SSH_CHMOD[ssh ➔ chmod +x]
        DG_CHECK{test -s 文件存在?}
        DG_CHECK -->|是| DG_OK[ok: downloaded ✅]
        DG_CHECK -->|否| DG_ERR[err: download failed ❌]
    end

    D_DOWNLOAD --> D_LOOP
    D_LOOP --> D_INSTALL[安装 & 启动]

    subgraph install_&_start
        IS_CMDS[拼接单条 SSH 命令]
        IS_CMDS --> IS_BIN{检测 Termux?}
        IS_BIN -->|Termux| IS_TERMUX[B = /data/data/com.termux/files/usr/bin]
        IS_BIN -->|标准 Linux| IS_STD[B = /usr/local/bin]
        IS_TERMUX --> IS_CP[chmod +x → cp 到 $B]
        IS_STD --> IS_CP
        IS_CP --> IS_GW{有 gateway 组件?}
        IS_GW -->|是| IS_GW_START[pkill 旧 → nohup 新 gateway]
        IS_GW -->|否| IS_WK
        IS_GW_START --> IS_WK{有 worker 组件?}
        IS_WK -->|是| IS_WK_START[pkill 旧 → nohup 新 worker --gw --node-id --region]
        IS_WK -->|否| IS_DONE
        IS_WK_START --> IS_DONE
    end

    D_INSTALL --> D_VERIFY[验证]
    
    subgraph verify
        V_GW{有 gateway?}
        V_GW -->|是| V_GW_CHECK[curl /api/health ➔ Healthy?]
        V_GW -->|否| V_WK
        V_GW_CHECK --> V_GW_OK[ok: Gateway ✅]:::green
        V_GW_CHECK --> V_GW_WARN[warn: Gateway N/A]:::yellow
        V_WK{有 worker?}
        V_WK -->|是| V_WK_CHECK[ssh ps aux ➔ 进程存在?]
        V_WK -->|否| V_DONE
        V_WK_CHECK --> V_WK_OK[ok: Worker running ✅]:::green
        V_WK_CHECK --> V_WK_WARN[warn: Worker not detected]:::yellow
        V_DONE[ok: Deploy done ✅]:::green
    end

    D_VERIFY --> D_DONE([done])

    %% ===== all 流程 =====
    ALL --> B_GO

    %% 样式
    classDef green fill:#a3d9a5,stroke:#333,stroke-width:1px
    classDef yellow fill:#ffe066,stroke:#333,stroke-width:1px
    classDef red fill:#f28b82,stroke:#333,stroke-width:1px
    classDef blue fill:#a8d4e6,stroke:#333,stroke-width:2px
    class START,PARSE blue
```

## 参数一览

| 参数 | 必须 | 默认值 | 说明 |
|------|------|--------|------|
| `host` | ✅ 是 | - | 目标机器 IP |
| `password` | ❌ 否 | 空（用 SSH key） | 密码 |
| `--component` | ❌ 否 | all | gateway/tui/worker/node 或逗号分隔 |
| `--port` | ❌ 否 | 22 | SSH 端口 |
| `--gateway` | ❌ 否 | host:8282 | Gateway 地址（自动补 http://） |
| `--node-id` | ❌ 否 | cqf-{IP最后一段} | Worker 节点 ID |
| `--region` | ❌ 否 | cn-east | Worker 区域 |
| `--user` | ❌ 否 | root | SSH 用户 |
| `--version` | ❌ 否 | deploy/version.txt | 构建版本号 |

## 数据流（单一方向）

```
Gateway 机器                         目标机器
┌──────────────┐                   ┌──────────────────┐
│  deploy/     │                   │                  │
│  computehub- │                   │  curl -sL ➔ ~/  │
│  worker-     │  ─── HTTP ───→   │  chmod +x       │
│  linux-arm64 │  /api/v1/        │  cp ➔ $BIN      │
│              │  download        │  nohup ➔ 启动    │
└──────────────┘                   │  ──→ --gw       │
                                   │       --node-id  │
                                   │       --region   │
                                   └──────────────────┘
```
