# 充电云 - 快速部署指南

## 一、环境要求

- Python 3.6+（前端静态服务器）
- Java 17+（后端，可选）
- Maven 3.6+（后端，可选）
- Node.js 18+（前端开发，可选）

## 二、快速启动（前端静态版）

### 方式1：Python服务器

```bash
cd frontend
python3 server.py
```

访问：http://localhost:8080

### 方式2：直接打开HTML

```bash
# 登录页
open frontend/login.html

# 管理后台
open frontend/index.html

# 官网首页
open frontend/home.html
```

## 三、完整部署（后端+前端）

### 1. 启动后端

```bash
cd backend
mvn spring-boot:run
```

后端默认端口：8080

### 2. 启动前端

```bash
cd frontend
npm install
npm run dev
```

前端默认端口：5173

## 四、项目结构

```
chargecloud-opc/
├── backend/                    # 后端代码
│   ├── pom.xml                 # Maven配置
│   ├── src/main/java/          # Java源码
│   │   └── com/chargecloud/
│   │       ├── entity/         # 实体类
│   │       ├── mapper/         # Mapper接口
│   │       ├── service/        # 服务层
│   │       └── controller/    # 控制器
│   ├── src/main/resources/
│   │   └── application.yml      # 配置文件
│   └── sql/
│       └── init.sql            # 数据库初始化
│
├── frontend/                   # 前端代码
│   ├── src/                    # Vue源码
│   │   ├── router/            # 路由配置
│   │   ├── layouts/           # 布局组件
│   │   └── views/             # 页面组件
│   ├── index.html             # 管理后台入口
│   ├── login.html             # 登录页（独立版）
│   ├── home.html              # 官网首页
│   ├── package.json           # 依赖配置
│   └── vite.config.js         # Vite配置
│
├── docs/                       # 项目文档
│   ├── PRD.md                 # 产品需求文档
│   ├── DATABASE.md            # 数据库设计
│   ├── API.md                 # API接口文档
│   ├── TECH_ARCHITECTURE.md   # 技术架构
│   ├── COMPETITOR_ANALYSIS.md # 竞品分析
│   ├── CUSTOMER_PROFILE.md    # 客户画像
│   ├── PRICING_STRATEGY.md    # 定价策略
│   ├── OPERATION_PLAN.md      # 运营计划
│   ├── FAQ.md                 # 常见问题(50条)
│   ├── USER_MANUAL.md         # 用户手册
│   ├── BRAND_GUIDE.md         # 品牌设计
│   ├── SALES_SCRIPT.md        # 销售话术
│   ├── MARKETING_COPY.md      # 营销文案
│   ├── CUSTOMER_SERVICE_FLOW.md # 客服流程
│   ├── KNOWLEDGE_BASE.md      # 知识库
│   ├── SERVICE_SCRIPTS.md     # 客服话术
│   ├── FINANCE_TEMPLATES.md   # 财务模板
│   ├── FINANCE/               # 财务文件夹
│   │   ├── INCOME_TEMPLATE.md
│   │   ├── COST_TEMPLATE.md
│   │   ├── CASHFLOW_TEMPLATE.md
│   │   └── MONTHLY_REPORT.md
│   └── ...
│
├── presentation.html          # PPT演示文稿
└── README.md                  # 本文件
```

## 五、数据库配置

### 1. 创建数据库

```sql
CREATE DATABASE chargecloud DEFAULT CHARACTER SET utf8mb4;
```

### 2. 执行初始化脚本

```bash
mysql -u root -p chargecloud < backend/sql/init.sql
```

### 3. 修改配置

编辑 `backend/src/main/resources/application.yml`：

```yaml
spring:
  datasource:
    url: jdbc:mysql://localhost:3306/chargecloud
    username: your_username
    password: your_password
```

## 六、API接口

### 充电站管理

- GET `/api/stations` - 获取充电站列表
- POST `/api/stations` - 创建充电站
- PUT `/api/stations/{id}` - 更新充电站
- DELETE `/api/stations/{id}` - 删除充电站

### 充电桩管理

- GET `/api/piles` - 获取充电桩列表
- POST `/api/piles` - 创建充电桩
- PUT `/api/piles/{id}` - 更新充电桩
- DELETE `/api/piles/{id}` - 删除充电桩

### 订单管理

- GET `/api/orders` - 获取订单列表
- GET `/api/orders/{id}` - 获取订单详情
- PUT `/api/orders/{id}/status` - 更新订单状态

## 七、部署到生产环境

### 方式1：云服务器部署

1. 购买云服务器（阿里云/腾讯云）
2. 安装JDK 17、MySQL、Nginx
3. 上传项目文件
4. 启动后端服务
5. 配置Nginx反向代理

### 方式2：容器化部署

```bash
# 构建镜像
docker build -t chargecloud-backend ./backend
docker build -t chargecloud-frontend ./frontend

# 运行容器
docker run -d -p 8080:8080 chargecloud-backend
docker run -d -p 80:80 chargecloud-frontend
```

### 方式3：静态托管

前端可以直接部署到：
- GitHub Pages
- Vercel
- Netlify
- 阿里云OSS

## 八、联系方式

- 官网：www.chargecloud.com
- 电话：400-888-8888
- 邮箱：contact@chargecloud.com

---

*文档版本：v1.0*
*更新时间：2026-03-21*