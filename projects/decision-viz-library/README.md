# 通用决策可视化库 (Decision Visualization Library)

**核心理念**: 一次开发，处处使用 - 标准化决策可视化组件

## 🎯 功能特性

### 核心可视化组件
- **雷达图对比**: 多维度方案对比
- **热力图分布**: 专家意见分布可视化
- **时间线展示**: 决策过程演进
- **散点图分析**: 风险收益分布
- **共识动画**: 共识形成过程动画

### 交互功能
- **实时权重调整**: 动态调整评估维度权重
- **假设分析工具**: 测试不同决策场景
- **数据导出**: 支持多种格式导出
- **响应式设计**: 适配各种设备尺寸

## 🏗️ 技术架构

### 三层架构
```
应用层 (Apps)      - 具体项目应用
组件层 (Components) - 可复用可视化组件  
核心层 (Core)      - 基础引擎和工具
```

### 技术栈
- **可视化引擎**: Plotly.js + D3.js
- **框架支持**: React/Vue/Svelte/原生JS
- **样式方案**: CSS Modules + 主题系统
- **构建工具**: Vite + Rollup

## 📦 安装使用

### NPM安装
```bash
npm install decision-viz-library
```

### CDN引入
```html
<script src="https://cdn.jsdelivr.net/npm/decision-viz-library/dist/decision-viz.min.js"></script>
```

## 🚀 快速开始

### React示例
```jsx
import { RadarChart, Heatmap, DecisionPanel } from 'decision-viz-library';

function App() {
  return (
    <DecisionPanel 
      decisionData={decisionData}
      onWeightChange={handleWeightChange}
    />
  );
}
```

### Vue示例
```vue
<template>
  <decision-panel 
    :decision-data="decisionData"
    @weight-change="handleWeightChange"
  />
</template>

<script>
import { DecisionPanel } from 'decision-viz-library/vue';

export default {
  components: { DecisionPanel }
}
</script>
```

## 🔧 开发指南

### 本地开发
```bash
git clone <repository>
cd decision-viz-library
npm install
npm run dev
```

### 构建发布
```bash
npm run build
npm run test
npm publish
```

## 📚 文档

- [组件文档](./docs/components.md)
- [API参考](./docs/api.md)
- [示例项目](./examples/)
- [主题定制](./docs/theming.md)

## 🤝 贡献指南

欢迎贡献代码！请阅读：[贡献指南](./CONTRIBUTING.md)

## 📄 许可证

MIT License

---

**开发状态**: 🟢 活跃开发中  
**最新版本**: v0.1.0  
**更新时间**: 2026-03-29