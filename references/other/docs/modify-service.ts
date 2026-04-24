#!/bin/bash
# 修改 service.ts 文件来添加 Android 支持

# 备份原文件
cp ~/openclaw/src/daemon/service.ts ~/openclaw/src/daemon/service.ts.backup2

# 在 systemd 导入后添加 Android 导入
sed -i '/\} from "\/systemd.js";/a\\nimport {\n  installAndroidService,\n  isAndroidServiceEnabled,\n  readAndroidServiceExecStart,\n  readAndroidServiceRuntime,\n  restartAndroidService,\n  stopAndroidService,\n  uninstallAndroidService,\n} from "./android.js";' ~/openclaw/src/daemon/service.ts

# 在 resolveGatewayService 函数中添加 Android 平台支持
sed -i '/if (process.platform === "win32") {/,/^  }$/ {\n  /^  }$/i\\n  if (process.platform === "android") {\n    return {\n      label: "Android Service",\n      loadedText: "enabled",\n      notLoadedText: "disabled",\n      install: async (args) =\u003e {\n        await installAndroidService(args);\n      },\n      uninstall: async (args) =\u003e {\n        await uninstallAndroidService(args);\n      },\n      stop: async (args) =\u003e {\n        await stopAndroidService({\n          stdout: args.stdout,\n          env: args.env,\n        });\n      },\n      restart: async (args) =\u003e {\n        await restartAndroidService({\n          stdout: args.stdout,\n          env: args.env,\n        });\n      },\n      isLoaded: async (args) =\u003e isAndroidServiceEnabled(args),\n      readCommand: readAndroidServiceExecStart,\n      readRuntime: async (env) =\u003e await readAndroidServiceRuntime(env),\n    };\n  }\n}' ~/openclaw/src/daemon/service.ts