# CHANGELOG

## [2.0.0] - 2026-04-29

### 新增
- **配置管理**: 支持环境变量 + .env 文件，不再硬编码 API Key
- **自定义异常**: ConfigurationError / AdapterTimeout / AdapterHTTPError / AdapterRateLimitError / AdapterResponseError
- **结构化日志**: JSON 格式文件日志 + 控制台日志
- **性能监控**: PerformanceStats 数据类，统计调用次数/延迟/错误率/Token 消耗
- **健康检查增强**: 异常自动记录到日志

### 改进
- **版本化管理**: 添加 `__version__` = "2.0.0"
- **错误处理**: 区分 401/404/400/429/500 等状态码
- **日志记录**: Token 使用量 + 对话记录

### 安全
- 🔴 API Key 不再硬编码，必须通过环境变量配置
- .env 文件已加入 .gitignore

### 技术
- 移除硬编码的 QWEN36_URL / QWEN36_KEY
- 使用 dataclass 封装配置
- 支持 from_env() 工厂方法

---

## [1.0.0] - 2026-04-24

### 新增
- 初始版本
- 统一适配层
- 3 种调用模式: ask() / ask_detailed() / ask_code()
- content 字段优先策略
- Token 使用量记录
- 对话调试日志

### 背景
- 发现 vLLM 部署的 qwen3.6-35b 所有输出在 reasoning 字段
- content 字段始终为 null
- 核心突破: reasoning > content fallback 策略
