# 股票交易软件 - 安装说明

## 一、环境要求

- Python 3.8+
- SQLite 3.x

## 二、安装步骤

### 1. 安装核心依赖

```bash
pip install fastapi uvicorn pydantic PyJWT requests
```

### 2. （可选）安装完整依赖

```bash
pip install pandas akshare
```

注意：pandas在Termux/Android环境可能安装困难，程序会自动降级运行。

### 3. 启动服务

```bash
cd backend
python main.py
```

### 4. 访问

- API文档: http://localhost:8000/docs
- 前端页面: 浏览器打开 `frontend/index.html`

## 三、默认账户

- 用户名: admin
- 密码: admin123
- 初始资金: 1,000,000元

## 四、Termux环境特殊说明

在Termux/Android环境下：

1. 部分依赖可能需要编译
2. 建议使用最小安装
3. 程序会自动降级处理缺失的功能

```bash
# Termux最小安装
pip install fastapi uvicorn pydantic PyJWT requests

# 启动
cd backend
python main.py
```

## 五、常见问题

### Q: 启动报错 "ModuleNotFoundError"

A: 安装缺失的依赖：
```bash
pip install <模块名>
```

### Q: 无法获取行情数据

A: 检查网络连接，或使用新浪财经作为备用数据源。

### Q: 前端无法连接后端

A: 确保后端已启动，检查端口8000是否被占用。

---

*最后更新：2026-03-21*