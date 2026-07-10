#!/usr/bin/env node
/**
 * OpenClaw Bridge v2 — 通过 openclaw CLI 发送消息
 * 用法: node openclaw-bridge.js <消息内容>
 * 输出: JSON Lines (type: done|error)
 */
const { execSync, spawn } = require('child_process');
const message = process.argv.slice(2).join(' ');
if (!message) { console.error('用法: node openclaw-bridge.js <消息内容>'); process.exit(1); }

async function main() {
  try {
    // 1. 发送消息
    execSync(`openclaw sessions send "main" "${message.replace(/"/g, '\\"')}"`, {
      timeout: 10000,
      stdio: 'pipe'
    });

    // 2. 轮询回复
    const startTime = Date.now();
    const timeout = 120000;
    let lastContent = '';

    while (Date.now() - startTime < timeout) {
      await new Promise(r => setTimeout(r, 1500));
      
      try {
        const history = execSync('openclaw sessions history "main" --limit 5', {
          timeout: 5000,
          stdio: 'pipe',
          encoding: 'utf-8'
        });

        const lines = history.split('\n').filter(l => l.trim());
        for (let i = lines.length - 1; i >= 0; i--) {
          const line = lines[i];
          if (line.includes('assistant') || line.includes('🤖') || line.includes('💻')) {
            // Extract content after the role label
            const parts = line.split(/[🤖💻]/);
            if (parts.length > 1) {
              const reply = parts[parts.length - 1].trim();
              if (reply && reply !== lastContent) {
                lastContent = reply;
              }
            }
          }
        }

        // Check if we have a reply
        if (lastContent) {
          // Wait a bit more to ensure complete
          await new Promise(r => setTimeout(r, 2000));
          process.stdout.write(JSON.stringify({ type: 'done', data: lastContent }) + '\n');
          return;
        }
      } catch (e) {
        // History command might fail, keep polling
      }
    }

    process.stdout.write(JSON.stringify({ type: 'error', data: 'Timeout waiting for reply' }) + '\n');
  } catch (err) {
    process.stdout.write(JSON.stringify({ type: 'error', data: err.message }) + '\n');
  }
}

main().catch(err => {
  process.stdout.write(JSON.stringify({ type: 'error', data: err.message }) + '\n');
});
