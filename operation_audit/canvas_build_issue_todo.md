# 🎯 Canvas打包问题 - 待后续解决

## 📋 问题概述
- **发现时间**: 2026-04-05 08:28
- **问题模块**: Canvas UI打包 (第一步构建步骤)
- **当前状态**: ❌ 阻塞，已跳过
- **优先级**: 🔄 后续处理

## 🔍 问题详情

### 错误信息
```
vendor/a2ui/renderers/lit/src/0.8/data/signal-model-processor.ts(19,29): 
error TS2307: Cannot find module 'signal-utils/array' or its corresponding type declarations.

vendor/a2ui/renderers/lit/src/0.8/data/signal-model-processor.ts(20,27): 
error TS2307: Cannot find module 'signal-utils/map' or its corresponding type declarations.

vendor/a2ui/renderers/lit/src/0.8/data/signal-model-processor.ts(21,30): 
error TS2307: Cannot find module 'signal-utils/object' or its corresponding type declarations.

vendor/a2ui/renderers/lit/src/0.8/data/signal-model-processor.ts(22,27): 
error TS2307: Cannot find module 'signal-utils/set' or its corresponding type declarations.

vendor/a2ui/renderers/lit/src/0.8/model.test.ts(17,20): 
error TS2307: Cannot find module 'node:assert' or its corresponding type declarations.
```

### 受影响文件
1. `vendor/a2ui/renderers/lit/src/0.8/data/signal-model-processor.ts`
2. `vendor/a2ui/renderers/lit/src/0.8/model.test.ts`

### 缺失依赖
- **signal-utils/array**
- **signal-utils/map**  
- **signal-utils/object**
- **signal-utils/set**
- **@types/node** (node:assert)

## 📁 相关配置

### 构建脚本
- **文件**: `scripts/bundle-a2ui.sh`
- **位置**: 构建流程第一步
- **功能**: A2UI组件打包

### 项目配置
- **package.json**: 已声明 `"signal-utils": "^0.21.1"`
- **但未安装**: pnpm list显示未安装

## 🎯 解决方案待办

### 短期修复
1. **安装缺失依赖**: 
   ```bash
   pnpm add signal-utils@^0.21.1
   pnpm add -D @types/node
   ```

2. **验证安装**: 
   ```bash
   pnpm list signal-utils
   pnpm list @types/node
   ```

3. **重新执行**: 
   ```bash
   pnpm canvas:a2ui:bundle
   ```

### 长期考虑
1. **依赖检查**: 确保所有声明依赖实际安装
2. **构建优化**: 改进Canvas打包脚本的错误处理
3. **文档更新**: 记录特殊的构建依赖要求

## ⚠️ 影响范围

### 当前影响
- ❌ Canvas UI打包步骤无法执行
- ✅ 其他构建步骤可继续 (已跳过第一步)
- ✅ 核心功能编译不受影响

### 功能影响
- **A2UI相关功能**: 可能受影响
- **Canvas渲染**: 可能缺少优化
- **核心网关功能**: 不受影响

## 🔄 处理状态

### 已采取行动
- ✅ 问题已识别和记录
- ✅ 构建流程已调整 (跳过第一步)
- ✅ 后续步骤继续执行

### 待处理
- 🔲 安装缺失依赖
- 🔲 验证Canvas打包
- 🔲 更新构建文档

## 📅 计划处理时间

### 建议处理时机
- **非紧急**: 可在下次构建前处理
- **优先级**: 中等 (影响特定功能)
- **预计耗时**: 15-30分钟

### 处理前提
- 稳定的网络环境
- 足够的存储空间
- 完整的依赖安装

## 📝 相关文件

### 问题记录
- 本文件: `canvas_build_issue_todo.md`
- 构建日志: 相关错误记录

### 配置文件  
- `package.json`: 依赖声明
- `scripts/bundle-a2ui.sh`: 构建脚本
- `tsconfig.json`: 编译配置

### 源代码
- `vendor/a2ui/renderers/lit/`: 问题模块
- `src/canvas-host/`: Canvas主机代码

---
*记录时间: 2026-04-05 08:41*
*记录人: 小智*
*计划: 后续网络稳定时处理*
*状态: 已跳过，待修复*