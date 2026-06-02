# WIN-UPG-001 Windows 远程升级标准流程

> v1.2 · 最后更新: 2026-06-02

---

## ⚡ 一句话总结

```json
// 三步走：编译 → 上传 → 两条命令搞定
// Step 1 (下载):   curl -sL -o C:\tmp\ch_new.exe <URL> && echo DL_OK
// Step 2 (替换+重启): taskkill > nul & ping -n 3 > nul & move > nul & start /b ... & echo DONE
```

---

## 一、核心规则

### ✅ `&` 链，不用 `&&`

```json
"command": "cmd /c taskkill /f /im computehub.exe > nul 2>&1 & ping -n 4 127.0.0.1 > nul & move /y C:\\tmp\\ch_new.exe C:\\computehub.exe > nul & start /b C:\\computehub.exe worker --gw http://x.x.x.x:8282 --node-id xxx --interval 3 --concurrent 4 --heartbeat 10 & echo DONE"
```

**理由**: `&&` + `start` 会导致 cmd 挂死不执行后续命令 → SIGTERM。`&` 每条命令独立跑，前一个失败不影响后面。

### 🚫 禁止

- ❌ 写 `.bat` 文件中转（转义爆炸）
- ❌ PowerShell Here-String（引号地狱）
- ❌ 多步任务串行（步间状态不可靠）
- ❌ `&&` 链配合 `start`（挂死陷阱）
- ❌ 依赖 `exit_code`（用 `dir` + `version` 确认）

---

## 二、标准步骤 (SOP)

### Phase 0：确认文件

```bash
curl -s http://<GW>:8282/api/v1/gallery/list | python3 -c "
import json,sys
for i in json.load(sys.stdin).get('data',[]):
    if 'windows' in i['name'].lower(): print(i['name'], i['size_human'])
"
# 没有就上传: bash scripts/gallery-upload.sh <GW> windows-amd64
```

### Phase 1：下载 → 15-30s (超时 120s)

```
cmd /c curl -sL -o C:\tmp\ch_new.exe <GW>/api/v1/files/computehub-windows-amd64.exe && echo DL_OK
```

### Phase 2：替换+重启 → 瞬间 (超时 45s)

```
cmd /c taskkill /f /im computehub.exe > nul 2>&1 & ping -n 4 127.0.0.1 > nul & move /y C:\tmp\ch_new.exe C:\computehub.exe > nul & start /b C:\computehub.exe worker --gw <GW>:8282 --node-id Windows-mobile --interval 3 --concurrent 4 --heartbeat 10 & echo DONE
```

### Phase 3：验证（等 45s 重新注册后）

```bash
# 确认版本
cmd /c C:\computehub.exe version

# 确认在在线
curl -s http://<GW>:8282/api/v1/nodes/list | python3 -c "import json,sys; [print(n['node_id'],n['status']) for n in json.load(sys.stdin)['data']]"
```

---

## 三、常见错误速查

| 症状 | 最可能原因 | 修复 |
|------|----------|------|
| 任务挂死→SIGTERM | `&&` + `start` 陷阱 | 换 `&` 链 |
| exit=0 但版本没变 | move 没执行 / curl 无声失败 | 用 `dir` 确认文件存在 |
| 下载 1-2MB | Invoke-WebRequest 失败 | 用 `curl` |
| 升级后没重连 | 节点名大小写不匹配 | 检查 `Windows-mobile` |

---

## 四、版本约定

- 位置: `deploy/{VERSION}/windows-amd64/computehub.exe`
- Gallery 名: `computehub-windows-amd64.exe`
- 上传: `bash scripts/gallery-upload.sh <GW> windows-amd64`
- 递增规则: 小改进 +0.0.1

---

## 📜 历史踩坑（为什么这么写）

**v1.3.3→v1.3.4 (50min)**: bat 中转→PowerShell Here-String→`&&` 链→`&` 链 ✅  
**v1.3.4→v1.3.5**: `&&`+`start` 挂死→`&` 链全部独立 ✅

**核心教训**: Windows 远程执行 = 信任降级。任何复杂度都能压缩成"下载 + 替换重启"两条命令。