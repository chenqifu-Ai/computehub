# 管理后台模块

## 模块说明
Vue3 + TypeScript 前端管理后台。

## 功能列表
- 内容发布系统
- 版本管理（灰度/回滚）
- 设备管理（在线监控）
- 数据看板
- 权限管理（RBAC）

## 目录结构
```
admin-backend/
├── src/
│   ├── views/              # 页面组件
│   │   ├── Dashboard.vue   # 数据看板
│   │   ├── ContentManage.vue  # 内容管理
│   │   ├── DeviceManage.vue   # 设备管理
│   │   └── Permission.vue     # 权限管理
│   ├── components/         # 公共组件
│   ├── store/              # Pinia状态管理
│   ├── api/                # API调用
│   └── router/             # 路由配置
├── public/
├── package.json
└── vite.config.ts
```

## 技术栈
- Vue 3.4 + Composition API
- TypeScript 5.3
- Element Plus 2.5
- Pinia 2.1
- Vite 5.0
