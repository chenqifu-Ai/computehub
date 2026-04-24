# 技术智能体 - 工作目录

## 当前任务
- [x] PRD文档初稿 ✅
- [ ] 技术架构设计（进行中）
- [ ] 数据库设计
- [ ] API接口设计

## 技术栈选型

### 后端
- **框架**：Spring Boot 3.x
- **语言**：Java 17
- **数据库**：MySQL 8.0 + Redis 7.x
- **消息队列**：RabbitMQ
- **搜索**：Elasticsearch（可选）

### 前端
- **管理后台**：Vue 3 + Element Plus
- **小程序**：微信原生
- **APP**：React Native（二期）

### 基础设施
- **云服务商**：阿里云/腾讯云（待定）
- **容器**：Docker + Kubernetes
- **CI/CD**：GitHub Actions
- **监控**：Prometheus + Grafana

## 数据库设计（草稿）

### 核心表
```sql
-- 充电站表
CREATE TABLE charging_station (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    name VARCHAR(100) NOT NULL COMMENT '站点名称',
    address VARCHAR(255) COMMENT '地址',
    longitude DECIMAL(10,7) COMMENT '经度',
    latitude DECIMAL(10,7) COMMENT '纬度',
    operator_id BIGINT COMMENT '运营商ID',
    status TINYINT DEFAULT 1 COMMENT '状态：1正常 0停用',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- 充电桩表
CREATE TABLE charging_pile (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    station_id BIGINT NOT NULL COMMENT '站点ID',
    name VARCHAR(50) COMMENT '充电桩名称',
    type TINYINT COMMENT '类型：1快充 2慢充',
    power DECIMAL(10,2) COMMENT '功率(kW)',
    status TINYINT COMMENT '状态：1在线 2离线 3故障',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- 充电订单表
CREATE TABLE charging_order (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_no VARCHAR(32) UNIQUE COMMENT '订单号',
    user_id BIGINT COMMENT '用户ID',
    pile_id BIGINT COMMENT '充电桩ID',
    start_time DATETIME COMMENT '开始时间',
    end_time DATETIME COMMENT '结束时间',
    energy DECIMAL(10,2) COMMENT '充电量(度)',
    amount DECIMAL(10,2) COMMENT '金额',
    status TINYINT COMMENT '状态：1充电中 2已完成 3已取消',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

## API设计（草稿）

### 充电站管理
```
GET    /api/v1/stations          # 站点列表
POST   /api/v1/stations          # 创建站点
GET    /api/v1/stations/{id}     # 站点详情
PUT    /api/v1/stations/{id}     # 更新站点
DELETE /api/v1/stations/{id}     # 删除站点
```

### 充电桩管理
```
GET    /api/v1/piles             # 充电桩列表
POST   /api/v1/piles             # 创建充电桩
GET    /api/v1/piles/{id}        # 充电桩详情
PUT    /api/v1/piles/{id}        # 更新充电桩
DELETE /api/v1/piles/{id}        # 删除充电桩
GET    /api/v1/piles/{id}/status # 充电桩状态
```

### 订单管理
```
GET    /api/v1/orders            # 订单列表
GET    /api/v1/orders/{id}       # 订单详情
POST   /api/v1/orders            # 创建订单（开始充电）
PUT    /api/v1/orders/{id}/end   # 结束订单
GET    /api/v1/orders/stats      # 订单统计
```

## 下一步工作
1. 完善数据库设计
2. 设计详细API接口
3. 选择云服务商
4. 搭建开发环境

---
*更新时间：2026-03-21*