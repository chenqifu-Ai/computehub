# 🧪 ComputeHub 测试指南

## 📋 测试体系概述

### 测试层级
```
单元测试 → 集成测试 → 系统测试 → 性能测试 → 验收测试
```

### 测试覆盖范围
- ✅ API 端点测试
- ✅ 节点管理测试  
- ✅ 任务调度测试
- ✅ 错误处理测试
- ✅ 性能基准测试
- ✅ 安全扫描测试

## 🚀 快速开始

### 运行完整测试套件
```bash
# 方式1: 直接运行Python测试
cd /root/.openclaw/workspace
python scripts/test_suite.py

# 方式2: 使用集成测试脚本  
./scripts/integration_test.sh

# 方式3: 使用Makefile（如果存在）
make test
```

### 运行特定测试
```bash
# 运行单个测试类
python -m unittest scripts.test_suite.ComputeHubTestSuite.test_01_health_check

# 运行多个测试
python -m unittest scripts.test_suite.ComputeHubTestSuite.test_01_health_check scripts.test_suite.ComputeHubTestSuite.test_02_node_registration
```

## 📊 测试用例详情

### 1. 健康检查测试 (`test_01_health_check`)
**目的**: 验证Gateway健康状态
**检查点**:
- API端点响应状态200
- 返回状态为"healthy"
- 响应时间<500ms

### 2. 节点注册测试 (`test_02_node_registration`)
**目的**: 验证节点管理功能
**检查点**:
- 节点列表查询正常
- 新节点注册成功
- 重复注册正确处理

### 3. 任务提交测试 (`test_03_task_submission`)
**目的**: 验证任务调度功能
**测试场景**:
- 基础命令执行
- 计算密集型任务
- 文件操作任务

### 4. 任务结果查询测试 (`test_04_task_result_query`)
**目的**: 验证结果查询接口
**检查点**:
- 正常任务结果查询
- 不存在任务错误处理
- 响应格式验证

### 5. 性能基准测试 (`test_05_performance_benchmark`)
**目的**: 建立性能基线
**指标**:
- API响应时间<500ms
- 并发处理能力
- 资源使用率

### 6. 错误处理测试 (`test_06_error_handling`)
**目的**: 验证异常情况处理
**测试场景**:
- 无效参数处理
- 超时处理
- 节点离线处理

## 🔧 CI/CD 集成

### GitHub Actions 工作流
```yaml
name: ComputeHub CI/CD Tests
on: [push, pull_request, schedule]
jobs:
  - test-suite      # 完整测试套件
  - api-monitoring  # API监控测试
  - security-scan   # 安全扫描
  - performance-benchmark # 性能测试
```

### 定时任务配置
```bash
# 每天凌晨2点运行完整测试
0 2 * * * cd /root/.openclaw/workspace && ./scripts/integration_test.sh >> logs/daily_test.log 2>&1

# 每5分钟运行API监控
*/5 * * * * cd /root/.openclaw/workspace && python scripts/api_monitor.py >> logs/api_monitor.log 2>&1
```

## 🐛 故障排查

### 常见问题

#### Q: 测试失败 "Connection refused"
**A**: 检查ComputeHub服务是否启动
```bash
# 检查服务状态
curl http://localhost:8282/api/v2/health

# 启动服务
cd projects/computehub && ./bin/computehub-gateway-v0.7.1
```

#### Q: API端点返回404
**A**: 检查API路径是否正确
```bash
# 正确的任务提交端点
POST /api/v1/tasks/submit

# 正确的节点列表端点  
GET /api/v1/nodes/list
```

#### Q: JSON解析错误
**A**: 检查命令中的特殊字符转义
```bash
# 错误示例（未转义引号）
{"command": "echo "test""}

# 正确示例（正确转义）
{"command": "echo \"test\""}
```

### 调试模式
```bash
# 启用详细日志
DEBUG=1 python scripts/test_suite.py

# 查看详细请求信息
import requests
response = requests.post(...)
print(f"Status: {response.status_code}")
print(f"Headers: {response.headers}")
print(f"Body: {response.text}")
```

## 📈 测试报告

### 生成测试报告
```bash
# 运行测试并生成HTML报告
python -m pytest scripts/test_suite.py -v --html=reports/test_report.html

# 生成JUnit格式报告（CI/CD集成）
python -m pytest scripts/test_suite.py -v --junitxml=reports/junit.xml
```

### 报告解读
- ✅ 绿色: 测试通过
- ⚠️ 黄色: 测试警告
- ❌ 红色: 测试失败
- 🔄 蓝色: 测试跳过

## 🛡️ 质量门禁

### 通过标准
- 单元测试覆盖率 ≥ 80%
- 集成测试通过率 100%
- 性能指标达标率 100% 
- 安全漏洞数量 0

### 失败处理
1. 立即通知开发团队
2. 阻止问题代码合并
3. 创建故障工单
4. 优先修复回归问题

---
*最后更新: 2026-05-08*
*测试维护团队: ComputeHub QA组*