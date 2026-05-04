# 中国知网(CNKI)专利爬取指南

## 📋 概述
由于CNKI具有严格的反爬机制和验证码保护，直接自动化爬取比较困难。本指南提供多种解决方案。

## 🔧 已尝试的自动化方案

### 1. 基础爬虫
- 位置: `cnki_patent_crawler.py`
- 状态: ❌ 失败 - 需要验证码

### 2. 高级爬虫（多策略）
- 位置: `cnki_patent_crawler_advanced.py`
- 状态: ❌ 失败 - 所有策略都被拦截

## 🎯 推荐解决方案

### 方案一：手动验证 + Cookie使用（最可靠）

#### 步骤：
1. **手动访问CNKI**
   ```bash
   # 在浏览器中打开
   https://kns.cnki.net
   ```

2. **完成验证码验证**
   - 完成滑块验证或图形验证码
   - 登录账号（如果需要）

3. **获取Cookie**
   - 按F12打开开发者工具
   - 转到Network标签页
   - 刷新页面
   - 复制Cookie字符串

4. **在爬虫中使用Cookie**
   ```python
   # 修改爬虫代码添加Cookie
   cookies = {
       'Ecp_ClientId': '你的ID',
       'Ecp_IpLoginFail': '你的值',
       'CNKI_UserInfo': '你的信息',
       # ... 其他Cookie
   }
   session.cookies.update(cookies)
   ```

### 方案二：使用公开专利数据源

#### 替代数据源：
1. **国家知识产权局**
   - 网址: http://pss-system.cnipa.gov.cn
   - 特点: 官方数据，免费但需要注册

2. **SooPAT专利搜索**
   - 网址: http://www.soopat.com
   - 特点: 界面友好，但有访问限制

3. **PatentGuru**
   - 网址: https://www.patentguru.com
   - 特点: 国际化，支持多语言

4. **Google Patents**
   - 网址: https://patents.google.com
   - 特点: 全球专利，英文界面

### 方案三：使用API服务（如有权限）

#### CNKI官方API：
- 需要机构订阅或购买API权限
- 提供结构化的专利数据
- 访问: https://apigateway.cnki.net

#### 第三方专利API：
- 智慧芽: https://www.zhihuiya.com
- 佰腾网: http://www.baiten.cn
- 需要商业订阅

## 🛠️ 技术挑战与解决方案

### 主要挑战：
1. **验证码机制** - 滑块/图形验证码
2. **登录要求** - 需要账号权限
3. **反爬检测** - IP限制、请求频率限制
4. **动态内容** - JavaScript渲染

### 解决方案：
```python
# 使用Selenium模拟浏览器
from selenium import webdriver
from selenium.webdriver.common.by import By

# 或者使用Playwright
from playwright.sync_api import sync_playwright

# 使用代理IP轮换
proxies = ['ip1:port', 'ip2:port', 'ip3:port']

# 添加随机延迟
time.sleep(random.uniform(1, 3))
```

## 📊 数据字段提取目标

### 基本专利信息：
- 专利标题
- 专利号/申请号
- 发明人
- 申请人
- 申请日期
- 公开日期
- IPC分类号
- 摘要
- 主权项

### 详细专利信息：
- 法律状态
- 引证信息
- 同族专利
- 全文链接

## 🔧 环境准备

### 所需库：
```bash
pip install requests beautifulsoup4 selenium playwright pandas
```

### 浏览器驱动：
```bash
# Chrome驱动
apt-get install chromium-chromedriver

# 或使用Playwright
playwright install chromium
```

## ⚠️ 法律与道德注意事项

1. **遵守robots.txt**
2. **尊重版权** - 仅用于研究目的
3. **控制请求频率** - 避免对服务器造成压力
4. **数据使用** - 遵守数据使用条款
5. **个人隐私** - 不收集个人信息

## 📈 性能优化建议

1. **使用多线程/异步**
2. **实现断点续爬**
3. **数据去重机制**
4. **错误重试机制**
5. **日志记录系统**

## 🎯 下一步行动

1. 尝试手动获取Cookie并测试
2. 考虑使用替代专利数据源
3. 如需大量数据，考虑购买API服务
4. 或者使用浏览器自动化工具(Selenium/Playwright)

## 📁 文件说明

- `cnki_patent_crawler.py` - 基础爬虫
- `cnki_patent_crawler_advanced.py` - 高级多策略爬虫
- `patent_crawling_guide.md` - 本指南

## 💡 技术支持

如需要进一步的帮助，可以提供：
1. 具体的专利搜索需求
2. 可用的API权限信息
3. 预算范围（如考虑商业解决方案）