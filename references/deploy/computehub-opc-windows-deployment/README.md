# ComputeHub-OPC v1.0.0 Windows 部署方案

## 📦 部署方式选择

### 方式一：Docker部署 (生产环境推荐)
```bash
# 运行一键部署脚本
./deploy-docker.ps1
```

### 方式二：.NET原生部署 (开发测试)
```bash
# 运行原生部署脚本  
./deploy-native.ps1
```

### 方式三：Windows服务部署 (后台运行)
```bash
# 运行服务部署脚本
./deploy-service.ps1
```

## 🚀 快速开始

### 1. 环境准备
```powershell
# 运行环境检查脚本
./check-prerequisites.ps1
```

### 2. 选择部署方式
根据需求选择上述三种方式之一

### 3. 验证部署
```powershell
# 运行验证脚本
./verify-deployment.ps1
```

## 📊 监控方案

### 实时监控
```powershell
# 启动性能监控
./monitor-performance.ps1
```

### 日志查看
```powershell
# 查看实时日志
./view-logs.ps1
```

---
*部署脚本位于 scripts/ 目录下*
*配置模板位于 configs/ 目录下*