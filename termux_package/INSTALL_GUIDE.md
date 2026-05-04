# Termux OpenClaw 安装指南

由于 Android 安全限制，无法直接生成 APK 安装包。
请按以下步骤安装：

## 方法一：Termux 官方安装
1. 从 F-Droid 下载 Termux APK
2. 安装后运行以下命令：

```bash
pkg update && pkg upgrade
pkg install python nodejs git
npm install -g @openclaw/cli
openclaw gateway start
```

## 方法二：使用 Termux:API
1. 安装 Termux 和 Termux:API
2. 运行安装脚本

## 方法三：自定义打包
如需完整环境打包，建议使用：
- Termux 备份功能
- 第三方打包工具
