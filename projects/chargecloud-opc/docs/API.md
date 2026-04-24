# 充电云SaaS平台 - API接口文档

## 接口规范

### 基础信息
- **Base URL**: `https://api.chargecloud.com/v1`
- **协议**: HTTPS
- **数据格式**: JSON
- **编码**: UTF-8
- **认证方式**: JWT Token

### 通用响应格式

```json
{
  "code": 0,
  "message": "success",
  "data": {},
  "timestamp": 1710979200000
}
```

### 错误码定义

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1001 | 参数错误 |
| 1002 | 认证失败 |
| 1003 | 权限不足 |
| 1004 | 资源不存在 |
| 2001 | 业务错误 |
| 3001 | 系统错误 |

---

## 一、认证接口

### 1.1 管理员登录

**POST** `/auth/admin/login`

**请求参数**:
```json
{
  "username": "admin",
  "password": "123456"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expireIn": 7200,
    "userInfo": {
      "id": 1,
      "username": "admin",
      "name": "管理员",
      "role": 1
    }
  }
}
```

### 1.2 用户登录（小程序）

**POST** `/auth/user/login`

**请求参数**:
```json
{
  "phone": "13800138000",
  "code": "123456"
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
    "expireIn": 7200,
    "userInfo": {
      "id": 1,
      "phone": "138****8000",
      "nickname": "用户123",
      "balance": 100.00,
      "level": 1
    }
  }
}
```

---

## 二、充电站管理接口

### 2.1 获取充电站列表

**GET** `/stations`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| city | string | 否 | 城市 |
| status | int | 否 | 状态 |
| page | int | 否 | 页码，默认1 |
| size | int | 否 | 每页数量，默认20 |

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 100,
    "page": 1,
    "size": 20,
    "list": [
      {
        "id": 1,
        "name": "朝阳区充电站",
        "address": "北京市朝阳区xxx",
        "longitude": 116.123456,
        "latitude": 39.123456,
        "totalPiles": 10,
        "availablePiles": 5,
        "status": 1
      }
    ]
  }
}
```

### 2.2 创建充电站

**POST** `/stations`

**请求参数**:
```json
{
  "name": "朝阳区充电站",
  "operatorId": 1,
  "province": "北京市",
  "city": "北京市",
  "district": "朝阳区",
  "address": "朝阳区xxx路xxx号",
  "longitude": 116.123456,
  "latitude": 39.123456,
  "parkingFee": 5.00
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "朝阳区充电站"
  }
}
```

### 2.3 获取充电站详情

**GET** `/stations/{id}`

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "id": 1,
    "name": "朝阳区充电站",
    "operatorId": 1,
    "operatorName": "XX充电运营",
    "province": "北京市",
    "city": "北京市",
    "district": "朝阳区",
    "address": "朝阳区xxx路xxx号",
    "longitude": 116.123456,
    "latitude": 39.123456,
    "totalPiles": 10,
    "availablePiles": 5,
    "parkingFee": 5.00,
    "status": 1,
    "createdAt": "2026-03-21 10:00:00"
  }
}
```

### 2.4 更新充电站

**PUT** `/stations/{id}`

**请求参数**:
```json
{
  "name": "朝阳区充电站（新）",
  "address": "朝阳区xxx路xxx号新址",
  "parkingFee": 6.00
}
```

### 2.5 删除充电站

**DELETE** `/stations/{id}`

---

## 三、充电桩管理接口

### 3.1 获取充电桩列表

**GET** `/piles`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| stationId | long | 否 | 站点ID |
| status | int | 否 | 状态 |
| type | int | 否 | 类型：1快充 2慢充 |
| page | int | 否 | 页码 |
| size | int | 否 | 每页数量 |

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "total": 50,
    "list": [
      {
        "id": 1,
        "stationId": 1,
        "stationName": "朝阳区充电站",
        "code": "P001",
        "name": "1号充电桩",
        "type": 1,
        "power": 120.00,
        "status": 1,
        "price": 1.20,
        "serviceFee": 0.80
      }
    ]
  }
}
```

### 3.2 创建充电桩

**POST** `/piles`

**请求参数**:
```json
{
  "stationId": 1,
  "code": "P001",
  "name": "1号充电桩",
  "type": 1,
  "power": 120.00,
  "voltage": 380,
  "current": 315,
  "price": 1.20,
  "serviceFee": 0.80,
  "connectorType": 1
}
```

### 3.3 获取充电桩实时状态

**GET** `/piles/{id}/status`

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "pileId": 1,
    "status": 1,
    "statusText": "空闲",
    "currentPower": 0,
    "voltage": 380,
    "current": 0,
    "todayEnergy": 150.50,
    "todayOrderCount": 12
  }
}
```

### 3.4 远程控制充电桩

**POST** `/piles/{id}/control`

**请求参数**:
```json
{
  "action": "restart",
  "params": {}
}
```

**action类型**:
- `start`: 启动
- `stop`: 停止
- `restart`: 重启
- `setPrice`: 设置价格

---

## 四、订单管理接口

### 4.1 创建订单（开始充电）

**POST** `/orders`

**请求参数**:
```json
{
  "pileId": 1,
  "userId": 1
}
```

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderId": 1,
    "orderNo": "C20260321100001",
    "pileId": 1,
    "pileName": "1号充电桩",
    "stationName": "朝阳区充电站",
    "status": 1,
    "startTime": "2026-03-21 10:00:00",
    "price": 1.20,
    "serviceFee": 0.80
  }
}
```

### 4.2 结束充电

**PUT** `/orders/{orderNo}/end`

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "orderId": 1,
    "orderNo": "C20260321100001",
    "status": 2,
    "endTime": "2026-03-21 11:30:00",
    "duration": 5400,
    "energy": 45.50,
    "electricityFee": 54.60,
    "serviceFee": 36.40,
    "totalAmount": 91.00
  }
}
```

### 4.3 获取订单列表

**GET** `/orders`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| userId | long | 否 | 用户ID |
| stationId | long | 否 | 站点ID |
| status | int | 否 | 状态 |
| startDate | date | 否 | 开始日期 |
| endDate | date | 否 | 结束日期 |
| page | int | 否 | 页码 |
| size | int | 否 | 每页数量 |

### 4.4 获取订单详情

**GET** `/orders/{orderNo}`

### 4.5 订单统计

**GET** `/orders/stats`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| stationId | long | 否 | 站点ID |
| operatorId | long | 否 | 运营商ID |
| startDate | date | 是 | 开始日期 |
| endDate | date | 是 | 结束日期 |

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "totalOrders": 1000,
    "totalEnergy": 5000.50,
    "totalAmount": 8000.00,
    "avgOrderAmount": 8.00,
    "avgEnergy": 5.00,
    "dailyStats": [
      {
        "date": "2026-03-21",
        "orders": 100,
        "energy": 500.50,
        "amount": 800.00
      }
    ]
  }
}
```

---

## 五、用户管理接口

### 5.1 获取用户列表

**GET** `/users`

### 5.2 获取用户详情

**GET** `/users/{id}`

### 5.3 用户充值

**POST** `/users/{id}/recharge`

**请求参数**:
```json
{
  "amount": 100.00,
  "payMethod": 2
}
```

### 5.4 用户余额变动记录

**GET** `/users/{id}/balance-logs`

---

## 六、运营商管理接口

### 6.1 获取运营商列表

**GET** `/operators`

### 6.2 创建运营商

**POST** `/operators`

**请求参数**:
```json
{
  "name": "XX充电运营有限公司",
  "contact": "张经理",
  "phone": "13800138000",
  "email": "test@example.com",
  "address": "北京市朝阳区xxx",
  "licenseNo": "91110000xxx"
}
```

### 6.3 更新运营商

**PUT** `/operators/{id}`

### 6.4 运营商数据统计

**GET** `/operators/{id}/stats`

---

## 七、财务管理接口

### 7.1 收入统计

**GET** `/finance/income/stats`

**请求参数**:

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| operatorId | long | 否 | 运营商ID |
| startDate | date | 是 | 开始日期 |
| endDate | date | 是 | 结束日期 |
| groupBy | string | 否 | 分组方式：day/month |

### 7.2 提现申请

**POST** `/finance/withdraw`

**请求参数**:
```json
{
  "operatorId": 1,
  "amount": 10000.00,
  "bankAccount": "xxx银行xxx账号"
}
```

### 7.3 发票管理

**GET** `/finance/invoices`

**POST** `/finance/invoices`

---

## 八、数据看板接口

### 8.1 平台概览

**GET** `/dashboard/overview`

**响应**:
```json
{
  "code": 0,
  "message": "success",
  "data": {
    "todayIncome": 5000.00,
    "todayOrders": 100,
    "todayEnergy": 500.50,
    "totalStations": 50,
    "totalPiles": 500,
    "onlinePiles": 480,
    "totalUsers": 1000,
    "activeUsersToday": 100
  }
}
```

### 8.2 运营商看板

**GET** `/dashboard/operator/{operatorId}`

### 8.3 站点看板

**GET** `/dashboard/station/{stationId}`

---

## 九、Webhook回调接口

### 9.1 充电桩状态变更

**POST** `/webhook/pile/status`

**请求参数**:
```json
{
  "pileId": 1,
  "status": 2,
  "timestamp": 1710979200000
}
```

### 9.2 订单状态变更

**POST** `/webhook/order/status`

**请求参数**:
```json
{
  "orderNo": "C20260321100001",
  "status": 2,
  "energy": 45.50,
  "amount": 91.00,
  "timestamp": 1710979200000
}
```

---

## 附录

### A. 充电桩状态码

| 状态码 | 说明 |
|--------|------|
| 1 | 空闲 |
| 2 | 充电中 |
| 3 | 离线 |
| 4 | 故障 |

### B. 订单状态码

| 状态码 | 说明 |
|--------|------|
| 1 | 充电中 |
| 2 | 已完成 |
| 3 | 已取消 |
| 4 | 异常 |

### C. 支付方式

| 方式 | 说明 |
|------|------|
| 1 | 余额支付 |
| 2 | 微信支付 |
| 3 | 支付宝 |

---
*文档版本：v1.0*
*创建时间：2026-03-21*