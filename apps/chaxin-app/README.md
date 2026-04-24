# 茶信客户端 APP

茶信（Chaxin）是一个用于与OpenClaw智能体通信的手机APP。

## 功能

- 📤 发送消息给智能体（小龙虾、红茶、老黑等）
- 📥 接收智能体回复
- 🟢 显示连接状态
- 💾 本地消息历史
- 🔔 推送通知（后台接收）

## 安装

### Android

1. 安装依赖：
```bash
npm install
```

2. 开发模式运行：
```bash
npx expo start
```

3. 构建APK：
```bash
npx expo build:android
# 或使用 EAS
npx eas build --platform android
```

### iOS

1. 需要Apple开发者账号
2. 使用 Expo 构建或手动打包

## 配置

修改 `App.js` 中的配置：

```javascript
const CONFIG = {
  SERVER_URL: 'http://192.168.1.17:8080', // 茶信服务器地址
  API_KEY: 'your-api-key',                 // API密钥
  NODE_ID: 'phone',                        // 手机节点ID
};
```

## 智能体列表

| ID | 名称 | 角色 |
|-----|------|------|
| xiaozhi | 小龙虾 🦞 | 个人助理 |
| hongcha | 红茶 🍵 | 团队协调 |
| laok | 老K 📊 | 研究员 |
| ali | 阿狸 🦊 | 执行员 |
| xinxin | 小信 📡 | 监控员 |
| laohei | 老黑 🔧 | 技术员 |

## 技术栈

- React Native + Expo
- AsyncStorage 本地存储
- Fetch API 网络请求

## 后端

茶信后端服务：
- 地址：http://192.168.1.17:8080
- 文档：`~/.openclaw/workspace/company/tools/chaxin/`

## 作者

OpenClaw Team