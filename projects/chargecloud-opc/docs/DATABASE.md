# 充电云SaaS平台 - 数据库设计文档

## 数据库概述
- **数据库类型**：MySQL 8.0
- **字符集**：utf8mb4
- **排序规则**：utf8mb4_unicode_ci

## ER图（简化版）

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   User      │     │  Station    │     │    Pile     │
├─────────────┤     ├─────────────┤     ├─────────────┤
│ id          │     │ id          │     │ id          │
│ phone       │     │ name        │     │ station_id  │──┐
│ nickname    │     │ address     │     │ name        │  │
│ balance     │     │ operator_id │──┐  │ type        │  │
│ status      │     │ status      │  │  │ power       │  │
└─────────────┘     └─────────────┘  │  │ status      │  │
        │                            │  └─────────────┘  │
        │                            │         │        │
        ▼                            │         │        │
┌─────────────┐     ┌─────────────┐  │         │        │
│    Order    │     │  Operator   │◄─┘         │        │
├─────────────┤     ├─────────────┤            │        │
│ id          │     │ id          │            │        │
│ order_no    │     │ name        │            │        │
│ user_id     │◄────│ contact     │            │        │
│ pile_id     │◄────│ status      │            │        │
│ energy      │     └─────────────┘            │        │
│ amount      │                                │        │
│ status      │◄───────────────────────────────┘        │
└─────────────┘                                        │
        │                                              │
        ▼                                              │
┌─────────────┐                                        │
│  Payment    │                                        │
├─────────────┤                                        │
│ id          │                                        │
│ order_id    │◄───────────────────────────────────────┘
│ amount      │
│ method      │
│ status      │
└─────────────┘
```

## 核心表结构

### 1. 用户表 (user)

```sql
CREATE TABLE `user` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '用户ID',
  `phone` VARCHAR(11) NOT NULL COMMENT '手机号',
  `password` VARCHAR(255) COMMENT '密码（加密）',
  `nickname` VARCHAR(50) COMMENT '昵称',
  `avatar` VARCHAR(255) COMMENT '头像URL',
  `balance` DECIMAL(10,2) DEFAULT 0 COMMENT '账户余额（元）',
  `level` TINYINT DEFAULT 1 COMMENT '等级：1普通 2VIP 3企业',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1正常 0禁用',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_phone` (`phone`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表';
```

### 2. 运营商表 (operator)

```sql
CREATE TABLE `operator` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '运营商ID',
  `name` VARCHAR(100) NOT NULL COMMENT '公司名称',
  `contact` VARCHAR(50) COMMENT '联系人',
  `phone` VARCHAR(11) COMMENT '联系电话',
  `email` VARCHAR(100) COMMENT '邮箱',
  `address` VARCHAR(255) COMMENT '地址',
  `license_no` VARCHAR(50) COMMENT '营业执照号',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1正常 0禁用',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='运营商表';
```

### 3. 充电站表 (charging_station)

```sql
CREATE TABLE `charging_station` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '站点ID',
  `name` VARCHAR(100) NOT NULL COMMENT '站点名称',
  `operator_id` BIGINT NOT NULL COMMENT '运营商ID',
  `province` VARCHAR(50) COMMENT '省份',
  `city` VARCHAR(50) COMMENT '城市',
  `district` VARCHAR(50) COMMENT '区县',
  `address` VARCHAR(255) COMMENT '详细地址',
  `longitude` DECIMAL(10,7) COMMENT '经度',
  `latitude` DECIMAL(10,7) COMMENT '纬度',
  `total_piles` INT DEFAULT 0 COMMENT '充电桩总数',
  `available_piles` INT DEFAULT 0 COMMENT '可用充电桩数',
  `parking_fee` DECIMAL(10,2) DEFAULT 0 COMMENT '停车费（元/小时）',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1正常 0停用',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  KEY `idx_operator` (`operator_id`),
  KEY `idx_city` (`city`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='充电站表';
```

### 4. 充电桩表 (charging_pile)

```sql
CREATE TABLE `charging_pile` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '充电桩ID',
  `station_id` BIGINT NOT NULL COMMENT '站点ID',
  `code` VARCHAR(50) COMMENT '充电桩编号',
  `name` VARCHAR(50) COMMENT '充电桩名称',
  `type` TINYINT DEFAULT 1 COMMENT '类型：1快充 2慢充',
  `power` DECIMAL(10,2) COMMENT '功率（kW）',
  `voltage` DECIMAL(10,2) COMMENT '电压（V）',
  `current` DECIMAL(10,2) COMMENT '电流（A）',
  `price` DECIMAL(10,2) COMMENT '电价（元/度）',
  `service_fee` DECIMAL(10,2) COMMENT '服务费（元/度）',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1空闲 2充电中 3离线 4故障',
  `connector_type` TINYINT DEFAULT 1 COMMENT '接口类型：1国标 2特斯拉',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_code` (`code`),
  KEY `idx_station` (`station_id`),
  KEY `idx_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='充电桩表';
```

### 5. 充电订单表 (charging_order)

```sql
CREATE TABLE `charging_order` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '订单ID',
  `order_no` VARCHAR(32) NOT NULL COMMENT '订单号',
  `user_id` BIGINT NOT NULL COMMENT '用户ID',
  `pile_id` BIGINT NOT NULL COMMENT '充电桩ID',
  `station_id` BIGINT NOT NULL COMMENT '站点ID',
  `operator_id` BIGINT NOT NULL COMMENT '运营商ID',
  `start_time` DATETIME COMMENT '开始时间',
  `end_time` DATETIME COMMENT '结束时间',
  `duration` INT DEFAULT 0 COMMENT '充电时长（秒）',
  `start_soc` TINYINT COMMENT '开始电量%',
  `end_soc` TINYINT COMMENT '结束电量%',
  `energy` DECIMAL(10,2) DEFAULT 0 COMMENT '充电量（度）',
  `electricity_fee` DECIMAL(10,2) DEFAULT 0 COMMENT '电费（元）',
  `service_fee` DECIMAL(10,2) DEFAULT 0 COMMENT '服务费（元）',
  `parking_fee` DECIMAL(10,2) DEFAULT 0 COMMENT '停车费（元）',
  `total_amount` DECIMAL(10,2) DEFAULT 0 COMMENT '总金额（元）',
  `pay_method` TINYINT COMMENT '支付方式：1余额 2微信 3支付宝',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1充电中 2已完成 3已取消 4异常',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_order_no` (`order_no`),
  KEY `idx_user` (`user_id`),
  KEY `idx_pile` (`pile_id`),
  KEY `idx_station` (`station_id`),
  KEY `idx_operator` (`operator_id`),
  KEY `idx_status` (`status`),
  KEY `idx_created` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='充电订单表';
```

### 6. 支付记录表 (payment_record)

```sql
CREATE TABLE `payment_record` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '记录ID',
  `order_id` BIGINT NOT NULL COMMENT '订单ID',
  `user_id` BIGINT NOT NULL COMMENT '用户ID',
  `transaction_no` VARCHAR(64) COMMENT '交易流水号',
  `amount` DECIMAL(10,2) NOT NULL COMMENT '支付金额（元）',
  `pay_method` TINYINT NOT NULL COMMENT '支付方式：1余额 2微信 3支付宝',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1待支付 2已支付 3已退款',
  `paid_at` DATETIME COMMENT '支付时间',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_transaction_no` (`transaction_no`),
  KEY `idx_order` (`order_id`),
  KEY `idx_user` (`user_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='支付记录表';
```

### 7. 价格策略表 (price_policy)

```sql
CREATE TABLE `price_policy` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '策略ID',
  `station_id` BIGINT NOT NULL COMMENT '站点ID',
  `name` VARCHAR(50) COMMENT '策略名称',
  `start_time` TIME COMMENT '开始时间',
  `end_time` TIME COMMENT '结束时间',
  `electricity_price` DECIMAL(10,2) COMMENT '电价（元/度）',
  `service_price` DECIMAL(10,2) COMMENT '服务费（元/度）',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1启用 0停用',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  PRIMARY KEY (`id`),
  KEY `idx_station` (`station_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='价格策略表';
```

### 8. 管理员表 (admin_user)

```sql
CREATE TABLE `admin_user` (
  `id` BIGINT NOT NULL AUTO_INCREMENT COMMENT '管理员ID',
  `username` VARCHAR(50) NOT NULL COMMENT '用户名',
  `password` VARCHAR(255) NOT NULL COMMENT '密码（加密）',
  `name` VARCHAR(50) COMMENT '姓名',
  `phone` VARCHAR(11) COMMENT '手机号',
  `email` VARCHAR(100) COMMENT '邮箱',
  `role` TINYINT DEFAULT 1 COMMENT '角色：1超管 2运营 3财务',
  `operator_id` BIGINT COMMENT '运营商ID（为空表示平台管理员）',
  `status` TINYINT DEFAULT 1 COMMENT '状态：1正常 0禁用',
  `last_login` DATETIME COMMENT '最后登录时间',
  `created_at` DATETIME DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
  `updated_at` DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
  PRIMARY KEY (`id`),
  UNIQUE KEY `uk_username` (`username`),
  KEY `idx_operator` (`operator_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='管理员表';
```

## 索引设计说明

1. **主键索引**：所有表使用BIGINT自增主键
2. **唯一索引**：订单号、交易流水号、用户手机号等
3. **普通索引**：外键关联字段、状态字段、时间字段
4. **联合索引**：按查询场景设计

## 数据量预估

| 表名 | 年增量 | 3年预估 |
|------|--------|---------|
| user | 10万 | 30万 |
| operator | 100 | 300 |
| charging_station | 1000 | 3000 |
| charging_pile | 5000 | 15000 |
| charging_order | 100万 | 300万 |
| payment_record | 100万 | 300万 |

---
*文档版本：v1.0*
*创建时间：2026-03-21*