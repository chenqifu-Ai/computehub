import { execFile } from "node:child_process";
import fs from "node:fs/promises";
import path from "node:path";
import { promisify } from "node:util";
import type { GatewayServiceRuntime } from "./service-runtime.js";
import { colorize, isRich, theme } from "../terminal/theme.js";
import {
  formatGatewayServiceDescription,
  LEGACY_GATEWAY_SYSTEMD_SERVICE_NAMES,
  resolveGatewaySystemdServiceName,
} from "./constants.js";
import { resolveHomeDir } from "./paths.js";
import { parseKeyValueOutput } from "./runtime-parse.js";

const execFileAsync = promisify(execFile);
const toPosixPath = (value: string) => value.replace(/\\/g, "/");

const formatLine = (label: string, value: string) => {
  const rich = isRich();
  return `${colorize(rich, theme.muted, `${label}:`)} ${colorize(rich, theme.command, value)}`;
};

// Android 特定的服务实现
export async function installAndroidService(args: {
  stdout?: NodeJS.WritableStream;
  env: Record<string, string | undefined>;
}): Promise<void> {
  const { stdout, env } = args;
  
  // 在 Android 上，我们使用简单的后台进程管理
  // 创建一个启动脚本
  const homeDir = resolveHomeDir(env);
  const scriptPath = path.join(homeDir, ".openclaw", "start-gateway.sh");
  
  const scriptContent = `#!/bin/bash
# OpenClaw Gateway startup script for Android
cd "${homeDir}"
nohup openclaw gateway start > ".openclaw/gateway.log" 2>&1 &
echo $! > ".openclaw/gateway.pid"
`;
  
  await fs.writeFile(scriptPath, scriptContent, { mode: 0o755 });
  
  if (stdout) {
    stdout.write(formatLine("Android service script", scriptPath) + "\n");
  }
}

export async function uninstallAndroidService(args: {
  stdout?: NodeJS.WritableStream;
  env: Record<string, string | undefined>;
}): Promise<void> {
  const { stdout, env } = args;
  const homeDir = resolveHomeDir(env);
  const scriptPath = path.join(homeDir, ".openclaw", "start-gateway.sh");
  const pidFile = path.join(homeDir, ".openclaw", "gateway.pid");
  
  try {
    await fs.unlink(scriptPath);
    await fs.unlink(pidFile);
  } catch (error) {
    // 文件可能不存在，忽略错误
  }
  
  if (stdout) {
    stdout.write("Android service script removed\n");
  }
}

export async function stopAndroidService(args: {
  stdout?: NodeJS.WritableStream;
  env: Record<string, string | undefined>;
}): Promise<void> {
  const { env } = args;
  const homeDir = resolveHomeDir(env);
  const pidFile = path.join(homeDir, ".openclaw", "gateway.pid");
  
  try {
    const pid = await fs.readFile(pidFile, "utf8").then(content => content.trim());
    if (pid) {
      await execFileAsync("kill", ["-TERM", pid]);
    }
  } catch (error) {
    // PID 文件可能不存在或进程已停止
  }
}

export async function restartAndroidService(args: {
  stdout?: NodeJS.WritableStream;
  env: Record<string, string | undefined>;
}): Promise<void> {
  await stopAndroidService(args);
  await new Promise(resolve => setTimeout(resolve, 1000)); // 等待1秒
  await installAndroidService(args);
  
  // 执行启动脚本
  const homeDir = resolveHomeDir(args.env);
  const scriptPath = path.join(homeDir, ".openclaw", "start-gateway.sh");
  await execFileAsync("bash", [scriptPath]);
}

export async function isAndroidServiceEnabled(args: {
  env: Record<string, string | undefined>;
}): Promise<boolean> {
  const homeDir = resolveHomeDir(args.env);
  const scriptPath = path.join(homeDir, ".openclaw", "start-gateway.sh");
  
  try {
    await fs.access(scriptPath);
    return true;
  } catch (error) {
    return false;
  }
}

export async function readAndroidServiceExecStart(env: Record<string, string | undefined>): Promise<{
  command: string;
  args: string[];
  environment?: Record<string, string>;
  sourcePath?: string;
} | null> {
  return {
    command: "openclaw",
    args: ["gateway", "start"],
    environment: {},
    sourcePath: path.join(resolveHomeDir(env), ".openclaw", "start-gateway.sh")
  };
}

export async function readAndroidServiceRuntime(env: Record<string, string | undefined>): Promise<GatewayServiceRuntime> {
  const homeDir = resolveHomeDir(env);
  const pidFile = path.join(homeDir, ".openclaw", "gateway.pid");
  
  let pid: string | undefined;
  let status: "running" | "stopped" = "stopped";
  
  try {
    pid = await fs.readFile(pidFile, "utf8").then(content => content.trim());
    if (pid) {
      // 检查进程是否在运行
      try {
        await execFileAsync("ps", ["-p", pid]);
        status = "running";
      } catch (error) {
        status = "stopped";
      }
    }
  } catch (error) {
    // PID 文件不存在
  }
  
  return {
    pid: pid ? parseInt(pid) : undefined,
    status,
    platform: "android",
    serviceType: "android-script"
  };
}