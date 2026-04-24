#!/bin/bash
# 在 service.ts 中添加 Android 平台支持

cd ~/openclaw/src/daemon

# 备份原文件
cp service.ts service.ts.backup2

# 在 win32 部分之后添加 Android 支持
sed -i '161a\\n  if (process.platform === "android") {\n    return {\n      label: "Android Service",\n      loadedText: "enabled",\n      notLoadedText: "disabled",\n      install: async (args) =\u003e {\n        await installAndroidService(args);\n      },\n      uninstall: async (args) =\u003e {\n        await uninstallAndroidService(args);\n      },\n      stop: async (极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘67% | 内存8.6G/11.3G | 负载正常
专家学习: 262极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘67% | 内存8.6G/11.3G | 负载正常
专家学习: 262篇文档
系统快照: ✅ 已创建 (第70个快照)
公司脉搏: ✅ 正常 (产出需关注)
任务执行: ✅ 脉搏检查完成 | 法律风险评估 | 214代码文件 | 188结果文件
风险等级: 🟡 中等偏高 (投资合规+内容合规风险)
下次检查: 极速版状态: ✅ 正常 (v2.5.3)
数据状态: ✅ 已完成监控分析
系统资源: 磁盘67% | 内存8.6G/11.3G | 负载正常
专家学习: 262篇文档
系统快照: ✅ 已创建 (第70个快照)
公司脉搏: ✅ 正常 (产出需关注)
任务执行: ✅ 脉搏检查完成 | 法律风险评估 | 214代码文件 | 188结果文件
风险等级: 🟡 中等偏高 (投资合规+内容合规风险)
下次检查: 18:31% | 内存8.6G/11.3G | 负载正常
专家学习: 262篇文档
系统快照: ✅ 已创建 (第70个快照)
公司脉搏: ✅ 正常 (产出需关注)
任务执行: ✅ 脉搏检查完成 | 法律风险评估 | 214代码文件 | 188结果文件
风险等级: 🟡 中等偏高 (投资合规+内容合规风险)
下次检查: 18:31