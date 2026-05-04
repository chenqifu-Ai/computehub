# 中国知网专利数据爬虫

专业的中国知网(kns.cnki.net)专利数据采集工具，专注于人工智能、机器学习、深度学习相关专利。

## 功能特点

- ✅ 专利搜索与数据提取
- ✅ 支持多关键词批量搜索
- ✅ 提取专利标题、专利号、申请人、发明人、摘要、申请日期等关键信息
- ✅ 结构化数据输出(JSON/CSV)
- ✅ 反爬虫机制处理
- ✅ 邮件自动发送功能

## 安装依赖

```bash
pip install -r requirements.txt
```

## 快速开始

### 1. 运行爬虫

```bash
python run_crawler.py
```

### 2. 使用高级爬虫(需要处理验证码)

```bash
python advanced_crawler.py
```

### 3. 配置邮件发送

编辑 `email_sender.py` 配置发件邮箱：

```python
sender_email = "your_email@qq.com"  # 发送邮箱
sender_password = "your_app_password"  # QQ邮箱授权码
receiver_email = "19525456@qq.com"  # 接收邮箱
```

然后运行：
```bash
python email_sender.py
```

## 文件结构

```
cnki_patent_crawler/
├── requirements.txt          # 依赖包
├── config.py                # 配置文件
├── utils.py                 # 工具函数
├── crawler.py               # 基础爬虫
├── advanced_crawler.py      # 高级爬虫(处理反爬)
├── run_crawler.py           # 主执行脚本
├── email_sender.py          # 邮件发送模块
├── README.md               # 说明文档
└── patents_data.json       # 输出文件(示例)
└── patents_data.csv        # 输出文件(示例)
```

## 数据字段

提取的专利数据包含以下字段：

| 字段名 | 描述 | 示例 |
|--------|------|------|
| title | 专利标题 | 基于深度学习的人工智能图像识别方法 |
| patent_number | 专利号 | CN202310123456.7 |
| applicant | 申请人 | 清华大学 |
| inventor | 发明人 | 张三; 李四; 王五 |
| application_date | 申请日期 | 2023-01-15 |
| abstract | 摘要 | 本发明涉及一种基于深度学习... |
| publication_date | 公开日期 | 2023-06-20 |
| ipc_class | IPC分类号 | G06V10/82 |
| source | 数据来源 | CNKI |

## 搜索关键词

默认搜索以下人工智能相关关键词：
- 人工智能, AI, Artificial Intelligence
- 机器学习, Machine Learning
- 深度学习, Deep Learning
- 神经网络, Neural Network
- 计算机视觉, Computer Vision
- 自然语言处理, NLP

可以在 `config.py` 中修改 `SEARCH_KEYWORDS` 列表。

## 反爬处理

知网有严格的反爬机制，本爬虫包含以下防护措施：

1. **随机User-Agent** - 使用多种浏览器标识
2. **请求延迟** - 随机2-5秒延迟
3. **会话保持** - 维护cookies
4. **错误重试** - 自动重试机制
5. **请求头模拟** - 完整浏览器头信息

## 注意事项

1. **法律合规** - 请遵守知网的使用条款和数据保护法规
2. **访问频率** - 控制请求频率，避免过度访问
3. **商业用途** - 数据仅限个人研究使用
4. **验证码** - 如遇验证码需要人工处理

## 故障排除

### 常见问题

1. **连接被拒绝** - 可能是IP被暂时限制，等待一段时间重试
2. **验证码出现** - 需要人工干预处理验证码
3. **数据为空** - 检查网络连接和关键词有效性

### 调试模式

设置更详细的日志输出：
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

## 许可证

本项目仅用于技术学习和研究目的，请合理使用。

## 更新日志

- 2024-01-15: 初始版本发布
- 2024-01-15: 添加邮件发送功能
- 2024-01-15: 完善反爬机制

## 联系方式

如有问题请联系: 19525456@qq.com