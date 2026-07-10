# Knowledge: AI大厅Web对话界面UI改造经验
> Type: lesson
> Source: ecs-p2ph
> Confidence: 0.8
> TTL: 30 days
> Tags: UI, AI大厅, 对话界面, CSS, 前端
> Timestamp: 2026-07-11T05:41:47+08:00

## Content

## AI大厅Web对话界面UI改造经验

### 背景
ComputeHub Gateway 的 /ai 页面（AI大厅v4）对话面板排版简陋，气泡样式平淡，缺少Markdown渲染。老大要求改得更好看。

### 改动内容
1. **气泡样式翻新**
   - 用户气泡：紫色渐变 (#7c3aed→#6d28d9)，右下角小折角
   - AI气泡：深色玻璃质感，左上角小折角，带微光晕
   - 弹入动画 msgBounceIn（从下方弹入+缩放）
   - 思考中呼吸灯脉冲效果

2. **Markdown渲染**
   - 代码块：深色背景+圆角+语言标签
   - 行内代码：金色高亮
   - 加粗/斜体/链接全部支持
   - 换行自动处理

3. **细节增强**
   - 流式输出橙色闪烁光标
   - 每条消息右下角显示 HH:MM 时间戳
   - 用户👤/AI🤖 头像小圆标
   - 思考过程可折叠

4. **输入栏优化**
   - 更大圆角(12px)，更舒适padding
   - 聚焦时发光边框
   - 发送按钮hover上浮效果

### 技术要点
- 文件位置：ComputeHub/web/ai.html（2323行）
- Gateway 每次请求从磁盘读取，修改后刷新即生效，无需重启
- 新增 renderMarkdown() 函数做简易Markdown转HTML
- 新增 escapeAttr() 安全转义
- 流式渲染在 askOllama/askAgent/askOpenClaw 三个函数中统一处理

### 效果
老大评价："效果不错" ✅
