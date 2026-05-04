# 🤝 贡献指南

感谢你对 ComputeHub 项目的关注！

## 📋 目录

- [行为准则](#行为准则)
- [如何贡献](#如何贡献)
- [开发流程](#开发流程)
- [代码规范](#代码规范)
- [提交规范](#提交规范)
- [测试要求](#测试要求)

---

## 行为准则

本项目采用 [Contributor Covenant](https://www.contributor-covenant.org/) 行为准则。

**我们的承诺**: 营造开放、友好、安全的社区环境。

**禁止行为**:
- 使用性暗示语言或图像
- 人身攻击或侮辱性评论
- 公开或私下骚扰
- 未经许可发布他人隐私信息

---

## 如何贡献

### 方式一：报告问题

发现问题？[创建一个 Issue](https://github.com/computehub/computehub/issues/new)

**好的 Issue 应包含**:
- 清晰的问题描述
- 复现步骤
- 预期行为
- 实际行为
- 环境信息 (OS, Python 版本等)

### 方式二：提交代码

1. Fork 项目
2. 创建分支
3. 提交代码
4. 发起 PR

### 方式三：改进文档

文档同样重要！欢迎:
- 修正错别字
- 补充说明
- 添加示例
- 翻译文档

### 方式四：社区建设

- 回答问题
- 分享使用经验
- 推广项目
- 组织活动

---

## 开发流程

### 1. 环境设置

```bash
# Fork 并克隆
git clone https://github.com/YOUR_USERNAME/computehub.git
cd computehub

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

### 2. 创建分支

```bash
# 功能开发
git checkout -b feature/your-feature-name

# Bug 修复
git checkout -b fix/issue-123

# 文档改进
git checkout -b docs/update-readme
```

### 3. 开发代码

遵循 [代码规范](#代码规范)

### 4. 运行测试

```bash
# 单元测试
pytest tests/unit

# 集成测试
pytest tests/integration

# 代码覆盖率
pytest --cov=computehub tests/
```

### 5. 提交代码

遵循 [提交规范](#提交规范)

### 6. 发起 PR

- 填写 PR 描述
- 关联 Issue
- 等待 CI 检查
- 响应 Review 意见

---

## 代码规范

### Python 代码

遵循 [PEP 8](https://pep8.org/) 规范:

```python
# ✅ 好的代码
def calculate_gpu_cost(gpu_count: int, hours: float) -> float:
    """计算 GPU 使用成本"""
    rate = 0.03  # $/GPU/hour
    return gpu_count * hours * rate

# ❌ 避免
def calc(c,h):return c*h*0.03
```

### 代码格式化

使用 [Black](https://black.readthedocs.io/):

```bash
black .
```

### 类型注解

鼓励使用类型注解:

```python
from typing import List, Dict, Optional

def get_nodes(status: str) -> List[Dict]:
    """获取节点列表"""
    pass
```

### 文档字符串

所有公共函数应有文档字符串:

```python
def submit_job(framework: str, gpu_count: int) -> Job:
    """
    提交计算任务
    
    Args:
        framework: 深度学习框架 (pytorch/tensorflow)
        gpu_count: GPU 数量
    
    Returns:
        Job 对象
    
    Raises:
        ValueError: 参数无效时
    """
    pass
```

---

## 提交规范

遵循 [Conventional Commits](https://www.conventionalcommits.org/):

### 格式

```
<type>(<scope>): <description>

[optional body]

[optional footer]
```

### Type 类型

- `feat`: 新功能
- `fix`: Bug 修复
- `docs`: 文档更新
- `style`: 代码格式 (不影响功能)
- `refactor`: 重构
- `test`: 测试相关
- `chore`: 构建/工具

### 示例

```bash
# 新功能
git commit -m "feat(scheduler): 添加智能负载均衡算法"

# Bug 修复
git commit -m "fix(node): 修复节点注册超时问题"

# 文档更新
git commit -m "docs(readme): 补充快速开始指南"

# 重构
git commit -m "refactor(api): 优化 API 响应结构"
```

---

## 测试要求

### 单元测试

所有新功能应包含单元测试:

```python
# tests/unit/test_scheduler.py
def test_gpu_cost_calculation():
    """测试 GPU 成本计算"""
    cost = calculate_gpu_cost(gpu_count=4, hours=24)
    assert cost == 2.88  # 4 * 24 * 0.03
```

### 集成测试

关键流程应有集成测试:

```python
# tests/integration/test_job_submission.py
def test_end_to_end_job_submission():
    """测试完整的任务提交流程"""
    client = ComputeClient()
    job = client.submit_job(framework="pytorch", gpu_count=2)
    assert job.status == "running"
```

### 测试覆盖率

- 新功能覆盖率 ≥ 80%
- 核心模块覆盖率 ≥ 90%

---

## PR 指南

### PR 模板

```markdown
## 描述
简要描述此 PR 的目的

## 相关 Issue
Closes #123

## 变更类型
- [ ] 新功能 (feat)
- [ ] Bug 修复 (fix)
- [ ] 文档更新 (docs)
- [ ] 代码重构 (refactor)
- [ ] 其他

## 测试
- [ ] 已添加单元测试
- [ ] 已添加集成测试
- [ ] 所有测试通过

## 截图 (如适用)
添加截图展示 UI 变更
```

### Review 流程

1. CI 检查通过
2. 至少 1 个 Maintainer 批准
3. 解决所有 Review 意见
4. 合并到主分支

---

## 发布流程

### 版本号规范

遵循 [Semantic Versioning](https://semver.org/):

- `MAJOR.MINOR.PATCH` (1.0.0)
- MAJOR: 不兼容变更
- MINOR: 向后兼容的功能
- PATCH: 向后兼容的 Bug 修复

### 发布步骤

1. 更新版本号
2. 更新 CHANGELOG.md
3. 创建 Git Tag
4. 发布到 PyPI
5. 发布 GitHub Release

---

## 🙏 感谢所有贡献者!

<a href="https://github.com/computehub/computehub/graphs/contributors">
  <img src="https://contrib.rocks/image?repo=computehub/computehub" />
</a>

---

Made with ❤️ by the ComputeHub Team
