# AI智能招商平台 - API接口文档

**文档编号：** AI-API-2026-001
**版本号：** v1.0
**编制日期：** 2026-05-09
**编制单位：** 厦门京云科技有限公司

---

## 1. 接口概述

### 1.1 基础信息

| 项目 | 值 |
|------|-----|
| 基础URL | `https://api.example.com/api/v1` |
| 认证方式 | JWT Bearer Token |
| 数据格式 | JSON (UTF-8) |
| 字符编码 | UTF-8 |

### 1.2 通用响应格式

```json
{
  "code": 200,
  "message": "success",
  "data": {},
  "timestamp": 1715241600000
}
```

### 1.3 通用错误码

| 错误码 | 含义 | 说明 |
|--------|------|------|
| 200 | 成功 | 请求处理成功 |
| 400 | 请求错误 | 参数校验失败 |
| 401 | 未认证 | Token无效或过期 |
| 403 | 禁止访问 | 权限不足 |
| 404 | 资源不存在 | 请求资源不存在 |
| 429 | 请求过于频繁 | 限流触发 |
| 500 | 服务器错误 | 内部异常 |

---

## 2. 认证接口

### 2.1 登录

```
POST /auth/login
```

**请求体：**
```json
{
  "username": "admin",
  "password": "encrypted_password"
}
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "access_token": "eyJhbGci...",
    "refresh_token": "eyJhbGci...",
    "expires_in": 7200,
    "token_type": "Bearer"
  }
}
```

### 2.2 刷新Token

```
POST /auth/refresh
```

---

## 3. AI智能体接口

### 3.1 语音识别

```
POST /ai/voice/recognize
```

**请求体：**
```json
{
  "audio_data": "base64_encoded_audio",
  "format": "wav",
  "sample_rate": 16000,
  "mode": "online"
}
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "text": "翻到加盟政策",
    "confidence": 0.98,
    "intent": "slide_change",
    "params": {
      "target": "policy"
    }
  }
}
```

### 3.2 语音问答

```
POST /ai/voice/ask
```

**请求体：**
```json
{
  "question": "加盟费多少钱？",
  "context": "当前演示场景ID"
}
```

**响应：**
```json
{
  "code": 200,
  "data": {
    "answer": "加盟费根据城市等级不同，一线城市5万元，二线城市3万元...",
    "source": "faq",
    "confidence": 0.95,
    "related_questions": ["保证金多少？", "有区域保护吗？"]
  }
}
```

### 3.3 自动讲解

```
POST /ai/presentation/start
PUT /ai/presentation/control
GET /ai/presentation/status
```

---

## 4. 招商全案接口

### 4.1 品牌管理

```
GET    /project/brands          # 品牌列表
GET    /project/brands/:id      # 品牌详情
POST   /project/brands          # 新增品牌
PUT    /project/brands/:id      # 更新品牌
DELETE /project/brands/:id      # 删除品牌
```

### 4.2 产品管理

```
GET    /project/products        # 产品列表
GET    /project/products/:id    # 产品详情
POST   /project/products        # 新增产品
PUT    /project/products/:id    # 更新产品
```

### 4.3 投资分析

```
GET    /project/investment      # 投资分析数据
GET    /project/profit          # 盈利分析数据
POST   /project/calc/roi        # ROI计算
```

---

## 5. 管理后台接口

### 5.1 内容发布

```
POST /admin/content/publish
```

**请求体：**
```json
{
  "version": "v2.1.0",
  "content_type": "full_project",
  "channels": ["all"],
  "description": "2026年春季招商全案更新"
}
```

### 5.2 设备管理

```
GET    /admin/devices           # 设备列表
GET    /admin/devices/:id       # 设备详情
PUT    /admin/devices/:id       # 设备配置
POST   /admin/devices/:id/force-update  # 强制更新
```

### 5.3 数据看板

```
GET /admin/dashboard/stats      # 统计数据
GET /admin/dashboard/heatmap    # 页面热力图
GET /admin/dashboard/faq-stats  # 问题统计
```

---

*详细接口文档见 Swagger/OpenAPI YAML 文件*
