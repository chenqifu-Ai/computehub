# 茶信外网中转部署方案

## 方案一：Cloudflare Workers（推荐）

### 优点
- 免费：每天10万请求
- 快速：全球CDN
- 简单：一个JS文件

### 部署步骤

```bash
# 1. 安装 wrangler
npm install -g wrangler

# 2. 登录 Cloudflare
wrangler login

# 3. 创建 KV 命名空间
wrangler kv:namespace create CHAXIN_KV

# 4. 创建 wrangler.toml
cat > wrangler.toml << EOF
name = "chaxin-relay"
main = "cloudflare_worker.js"
compatibility_date = "2024-01-01"

[[kv_namespaces]]
binding = "CHAXIN_KV"
id = "你的KV命名空间ID"
EOF

# 5. 部署
wrangler deploy
```

### 使用
部署后得到 URL：`https://chaxin-relay.你的账号.workers.dev`

```bash
# 发送消息
curl -X POST https://chaxin-relay.xxx.workers.dev/msg/send \
  -H "Authorization: Bearer 8e6253b4..." \
  -H "Content-Type: application/json" \
  -d '{"from":"xiaozhi","to":"hongcha","subject":"测试","body":"你好"}'

# 接收消息
curl "https://chaxin-relay.xxx.workers.dev/msg/recv?to=hongcha&key=8e6253b4..."
```

## 方案二：GitHub Gist（临时方案）

用 GitHub Gist 作为共享存储：

```python
# 用 Gist 存储消息
import requests

GIST_ID = "你的Gist ID"
GITHUB_TOKEN = "你的GitHub Token"

def send_message(to, msg):
    # 更新 Gist
    pass

def recv_messages(to):
    # 读取 Gist
    pass
```

## 方案三：Supabase（免费数据库）

1. 注册 https://supabase.com（免费500MB）
2. 创建表：
```sql
CREATE TABLE messages (
  id SERIAL PRIMARY KEY,
  sender TEXT,
  recipient TEXT,
  subject TEXT,
  body TEXT,
  timestamp TIMESTAMPTZ DEFAULT NOW()
);
```
3. 用 PostgREST API 读写

## 当前状态

- 本地消息服务：✅ 运行中（8080端口）
- 云端中转：❌ 需要部署
- 外网访问：❌ 需要配置

## 下一步

1. 选择一个云服务（Cloudflare/Supabase）
2. 部署中转服务
3. 更新客户端配置