---
name: web-automation
description: Web automation skill for autonomous browser tasks - clicking, filling forms, scraping data, login flows, and multi-step web interactions. Use when user requests web-based tasks like "登录某网站", "帮我填表单", "抓取网页数据", "自动点击", "网页截图", "搜索并整理", or any browser automation need. Works with Chrome DevTools Protocol (CDP). Requires Chrome running with --remote-debugging-port=9222.
---

# Web Automation Skill

通过 Chrome DevTools Protocol (CDP) 控制浏览器进行自动化操作。支持点、填、爬、登录等常见网页任务。

## 核心能力

| 功能 | 说明 | 示例 |
|------|------|------|
| **自动点击** | 查找并点击元素 | "点击登录按钮" |
| **自动填表** | 填写表单字段 | "填写姓名和邮箱" |
| **数据抓取** | 提取表格/文本 | "抓取商品列表数据" |
| **登录流程** | 自动登录网站 | "登录淘宝" |
| **网页搜索** | Google/百度搜索 | "搜索最新AI新闻" |
| **截图** | 保存网页截图 | "截图当前页面" |

## 前置要求

Chrome 必须以调试模式运行：

```bash
# macOS
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome --remote-debugging-port=9222

# Windows
chrome.exe --remote-debugging-port=9222

# Linux
google-chrome --remote-debugging-port=9222

# 或使用脚本
chrome-debug
```

## 工作流程

### 1. 检查环境

首先确认 Chrome CDP 连接：

```bash
curl -s http://localhost:9222/json/version
```

### 2. 执行任务

根据任务类型选择方法：

#### 搜索任务
```bash
python3 scripts/browser_tool.py search "搜索关键词" 10
```

#### 打开网页
```bash
python3 scripts/browser_tool.py open "https://example.com"
```

#### 提取文本
```bash
python3 scripts/browser_tool.py text "https://example.com" "article"
```

#### 提取表格
```bash
python3 scripts/browser_tool.py table "https://example.com/data" 0
```

#### 截图
```bash
python3 scripts/browser_tool.py screenshot "https://example.com" /tmp/screenshot.png
```

### 3. 高级自动化 (page-agent)

对于复杂多步骤任务，使用 page-agent 进行自主执行：

```javascript
// 注入 page-agent
(function(){
  if(window.__pa_ready) return JSON.stringify({status:'ready'});
  return new Promise(function(resolve,reject){
    var s=document.createElement('script');
    s.src='https://cdn.jsdelivr.net/npm/page-agent@1/dist/iife/page-agent.demo.js';
    s.onload=function(){
      setTimeout(function(){
        if(!window.pageAgent) return reject('init failed');
        window.__pa_ready=true;
        resolve(JSON.stringify({status:'loaded'}));
      },2000);
    };
    s.onerror=function(){reject('CDN load failed')};
    document.head.appendChild(s);
  });
})()
```

```javascript
// 执行任务
(async function(){
  try{
    var r=await window.pageAgent.execute('点击登录按钮，输入邮箱user@example.com和密码pass123，然后提交');
    return JSON.stringify({success:r.success,data:r.data});
  }catch(e){
    return JSON.stringify({success:false,data:String(e)});
  }
})()
```

## 自动意图识别

当用户说以下内容时，自动执行对应操作：

| 用户说法 | 操作 | 示例 |
|---------|------|------|
| "搜索 xxx" | Google 搜索 | "搜索AI新闻" |
| "打开 xxx" | 打开网页 | "打开百度" |
| "抓取 xxx 数据" | 提取数据 | "抓取股票数据" |
| "截图" | 截取屏幕 | "截图当前页面" |
| "查一下 xxx" | 搜索+整理 | "查一下天气" |
| "登录 xxx" | 登录流程 | "登录淘宝" |
| "填写 xxx" | 填表 | "填写注册表单" |

## 故障排查

### Chrome 未连接
```
Error: connect ECONNREFUSED 127.0.0.1:9222
```
**解决**: 启动 Chrome 调试模式

### 页面加载超时
增加等待时间或检查网络

### 元素找不到
使用浏览器 DevTools 验证选择器

### 验证码阻塞
通知用户手动处理验证码

## 更新机制

本技能每日自动更新，从以下来源同步：
- page-agent: https://github.com/nicepkg/page-agent
- browser-automation: https://github.com/nardwang2026/openclaw-browser-automation-skill

## 脚本参考

详见 [scripts/](scripts/) 目录：
- `browser_tool.py` - 核心浏览器自动化工具
- `page_agent.py` - page-agent 封装

## 参考资料

详见 [references/](references/) 目录：
- `intent-parsing.md` - 意图识别指南
- `selectors.md` - CSS选择器参考
- `api-reference.md` - CDP API 参考