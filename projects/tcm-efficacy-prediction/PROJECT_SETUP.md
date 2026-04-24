# 🚀 中医药疗效预测机器学习项目 - 完整工程设置指南

## 📋 项目概述
这是一个完整的中医药疗效预测机器学习项目，包含从数据预处理到模型部署的全流程。

## 🎯 快速开始

### 1. 环境设置
```bash
# 创建conda环境
conda create -n tcm-ml python=3.9
conda activate tcm-ml

# 安装依赖
pip install -r requirements.txt

# 或者使用Docker
docker build -t tcm-ml-project .
docker run -it tcm-ml-project
```

### 2. 项目结构
```
tcm-efficacy-prediction/
├── 📁 data/                 # 数据目录
├── 📁 src/                  # 源代码
├── 📁 notebooks/            # Jupyter笔记本
├── 📁 config/              # 配置文件
├── 📁 tests/               # 测试文件
├── 📁 docs/                # 文档
├── 📁 web_app/             # Web应用
├── 📄 requirements.txt     # Python依赖
├── 📄 Dockerfile           # Docker配置
├── 📄 docker-compose.yml   # Docker Compose
└── 📄 README.md           # 项目说明
```

### 3. 运行流程
1. 数据预处理: `python src/data_processing/data_loader.py`
2. 特征工程: `python src/feature_engineering/feature_extractor.py`
3. 模型训练: `python src/model_training/xgboost_trainer.py`
4. 模型评估: `python src/evaluation/model_evaluator.py`
5. 启动API: `python src/deployment/api_server.py`

## 🛠️ 技术栈
- **机器学习**: Scikit-learn, XGBoost, TensorFlow
- **Web框架**: Django, React
- **数据库**: PostgreSQL, Redis
- **部署**: Docker, Kubernetes
- **监控**: Prometheus, Grafana

## 📊 数据说明
项目使用10,000例真实患者数据，包含：
- 患者基本信息
- 中医四诊数据
- 治疗方案参数
- 疗效评估结果

## 🚀 快速演示
```bash
# 克隆项目
git clone <repository-url>
cd tcm-efficacy-prediction

# 安装依赖
pip install -r requirements.txt

# 运行演示
python demo/demo_pipeline.py
```

## 📞 支持
如有问题，请提交Issue或联系项目维护者。

---
*项目创建时间: 2026-04-14*