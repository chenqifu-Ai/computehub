# 自然语言意图解析指南

根据用户的自然语言输入，自动识别意图并调用相应的浏览器操作。

## 意图识别模式

### 1. 搜索意图
**关键词**: 搜索、查找、查一下、找一下、搜一下、google、谷歌、帮我查

**示例**: 
- "搜索A股热门股"
- "帮我查一下今天的天气"
- "找一下Python教程"

**自动执行**:
```python
import asyncio
from scripts.browser_tool import search_google

query = "提取用户搜索词"  # 去掉"搜索"、"帮我"等前缀
results = asyncio.run(search_google(query, 10))
# 整理成易读格式返回
```

---

### 2. 打开网页意图
**关键词**: 打开、访问、进入、查看、去
**URL特征**: 包含 .com, .cn, .org, .net, .io, .ai, http

**示例**:
- "打开百度"
- "访问 github.com"
- "去东方财富网"

**自动执行**:
```python
import asyncio
from scripts.browser_tool import open_url

url = "提取的URL"  # 自动补全 https://
result = asyncio.run(open_url(url))
```

---

### 3. 数据提取意图
**关键词**: 抓取、提取、获取数据、整理、汇总
**上下文**: 涉及表格、列表、股票数据、价格信息等

**示例**:
- "抓取这个页面的股票数据"
- "提取表格中的信息"
- "整理这篇文章的内容"

**自动执行**:
```python
import asyncio
from scripts.browser_tool import extract_table, get_page_text

# 如果是表格数据
data = asyncio.run(extract_table(url, 0))

# 如果是文本内容
text = asyncio.run(get_page_text(url, selector))
```

---

### 4. 截图意图
**关键词**: 截图、截屏、保存页面、拍照

**示例**:
- "截图这个网页"
- "把当前页面保存下来"

**自动执行**:
```python
import asyncio
from scripts.browser_tool import screenshot

path = asyncio.run(screenshot(url, "/tmp/screenshot.png"))
```

---

## 自动工作流程

当识别到用户意图时，按以下步骤自动执行：

1. **检查 Chrome 状态**
   ```python
   status = asyncio.run(check_status())
   if not status['connected']:
       # 提示用户启动 Chrome 调试模式
   ```

2. **解析意图类型**
   - 搜索 → 调用 `search_google()`
   - 打开网页 → 调用 `open_url()`
   - 提取数据 → 调用 `extract_table()` 或 `get_page_text()`
   - 截图 → 调用 `screenshot()`

3. **执行并整理结果**
   - 执行相应的浏览器操作
   - 将结果整理成人类易读的格式
   - 必要时继续深入操作（如搜索结果后打开详情页）

4. **错误处理**
   - Chrome 未启动 → 提示启动命令
   - 页面加载失败 → 重试或提示检查网络
   - 选择器找不到 → 尝试其他选择器

---

## 复杂场景处理

### 场景: "帮我搜索A股热门股并整理"

自动执行流程:
1. 识别为"搜索 + 数据整理"意图
2. 执行 `search_google("A股热门股", 10)`
3. 获取搜索结果链接
4. 打开第一个相关页面
5. 提取页面关键信息
6. 整理成表格/列表返回

### 场景: "截图并保存"

自动执行流程:
1. 识别为"截图"意图
2. 执行 `screenshot(None, "/tmp/save.png")`  # 截图当前页面
3. 告知用户保存路径

### 场景: "打开这个网站抓取数据"

自动执行流程:
1. 识别"打开 + 抓取"复合意图
2. 先执行 `open_url(url)`
3. 等待页面加载
4. 执行 `extract_table()` 或 `get_page_text()`
5. 返回提取的数据
