# 股票交易软件 - 部署指南

## 一、环境要求

| 组件 | 版本要求 |
|------|----------|
| Python | 3.8+ |
| Node.js | 16+（可选，仅前端开发） |
| SQLite | 3.x |

## 二、本地部署

### 方式一：一键启动

```bash
# Linux/Mac
chmod +x start.sh
./start.sh

# Windows
双击 start.bat
```

### 方式二：手动启动

```bash
# 1. 进入后端目录
cd backend

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python main.py
```

### 访问地址

- **后端API**: http://localhost:8000
- **API文档**: http://localhost:8000/docs
- **前端页面**: 浏览器打开 `frontend/index.html`

## 三、Docker部署

### 构建镜像

```bash
docker build -t stock-trading:latest .
```

### 运行容器

```bash
docker run -d \
  --name stock-trading \
  -p 8000:8000 \
  -v ./data:/app/backend/data \
  stock-trading:latest
```

### 使用Docker Compose

```bash
docker-compose up -d
```

## 四、生产环境部署

### 1. 使用Gunicorn

```bash
pip install gunicorn

gunicorn main:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:8000
```

### 2. 使用Nginx反向代理

```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /static {
        alias /path/to/frontend;
    }
}
```

### 3. 使用Systemd服务

```ini
# /etc/systemd/system/stock-trading.service
[Unit]
Description=Stock Trading API
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/opt/stock-trading/backend
ExecStart=/usr/bin/python3 main.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
# 启用服务
sudo systemctl enable stock-trading
sudo systemctl start stock-trading
```

## 五、配置说明

### 数据源配置

编辑 `backend/config/datasource.py`:

```python
# 使用AKShare（免费）
PRIMARY_SOURCE = "akshare"

# 或使用Tushare（需要token）
PRIMARY_SOURCE = "tushare"
TUSHARE_TOKEN = "your-token-here"
```

### 数据库配置

默认使用SQLite，数据文件在 `backend/data/stock_trading.db`

### 端口配置

编辑 `backend/config/config.py`:

```python
HOST = "0.0.0.0"
PORT = 8000
```

## 六、常见问题

### Q: 无法获取行情数据？

A: 检查网络连接，或切换数据源：
- AKShare需要网络
- Tushare需要注册获取token
- 新浪财经作为备用

### Q: 启动报错？

A: 检查依赖安装：
```bash
pip install -r requirements.txt
```

### Q: 前端无法连接后端？

A: 检查CORS配置，确保后端已启动。

## 七、安全建议

生产环境建议：

1. **修改默认密码**
   - 默认账户 admin/admin123

2. **启用HTTPS**
   - 使用Let's Encrypt免费证书

3. **限制访问**
   - 使用防火墙限制API访问
   - 仅开放必要端口

4. **定期备份**
   - 备份SQLite数据库文件

---

*最后更新：2026-03-21*