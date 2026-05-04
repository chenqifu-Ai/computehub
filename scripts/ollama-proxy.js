#!/usr/bin/env node
/**
 * Ollama 反向代理 - 自动切换主备服务器
 * 监听本地端口，转发请求到主/备服务器
 */

const http = require('http');
const https = require('https');

// 配置
const LOCAL_PORT = 11435;
const PRIMARY = {
  host: '192.168.1.7',
  port: 11434,
  protocol: 'http'
};
const BACKUP = {
  host: 'ollama.com',
  port: 443,
  protocol: 'https',
  apiKey: '8e6253b418564cd4b4a3428f927ee6f0.3g95X2YSoELm9knHxHNci1ii'
};

let currentServer = 'primary';
let lastCheck = 0;
const CHECK_INTERVAL = 30000; // 30秒检查一次

// 日志
function log(msg) {
  console.log(`[${new Date().toISOString()}] ${msg}`);
}

// 检查服务器
function checkServer(target) {
  return new Promise((resolve) => {
    const timeout = target === 'primary' ? 10000 : 15000;
    const start = Date.now();
    
    const module = target === 'primary' ? http : https;
    const options = {
      hostname: target === 'primary' ? PRIMARY.host : BACKUP.host,
      port: target === 'primary' ? PRIMARY.port : BACKUP.port,
      path: '/api/tags',
      method: 'GET',
      timeout: timeout
    };
    
    if (target === 'backup') {
      options.headers = { 'Authorization': `Bearer ${BACKUP.apiKey}` };
    }
    
    const req = module.request(options, (res) => {
      resolve(res.statusCode === 200);
    });
    
    req.on('error', () => resolve(false));
    req.on('timeout', () => { req.destroy(); resolve(false); });
    req.end();
  });
}

// 获取当前活跃服务器
async function getActiveServer() {
  const now = Date.now();
  
  // 定期检查主服务器
  if (now - lastCheck > CHECK_INTERVAL) {
    lastCheck = now;
    
    const primaryOk = await checkServer('primary');
    
    if (primaryOk && currentServer === 'backup') {
      log('✅ 主服务器恢复，切回主服务器');
      currentServer = 'primary';
    } else if (!primaryOk && currentServer === 'primary') {
      log('❌ 主服务器无响应，切换到备用服务器');
      currentServer = 'backup';
    }
  }
  
  return currentServer;
}

// 代理请求
async function proxyRequest(clientReq, clientRes) {
  const server = await getActiveServer();
  const target = server === 'primary' ? PRIMARY : BACKUP;
  const module = server === 'primary' ? http : https;
  
  const options = {
    hostname: target.host,
    port: target.port,
    path: clientReq.url,
    method: clientReq.method,
    headers: { ...clientReq.headers }
  };
  
  // 备用服务器需要API Key
  if (server === 'backup') {
    options.headers['Authorization'] = `Bearer ${BACKUP.apiKey}`;
  }
  
  // 移除可能冲突的头
  delete options.headers['host'];
  delete options.headers['content-length'];
  
  const proxyReq = module.request(options, (proxyRes) => {
    clientRes.writeHead(proxyRes.statusCode, proxyRes.headers);
    proxyRes.pipe(clientRes);
  });
  
  proxyReq.on('error', (err) => {
    log(`代理错误: ${err.message}`);
    // 尝试备用服务器
    if (server === 'primary') {
      log('尝试备用服务器...');
      currentServer = 'backup';
    }
    clientRes.writeHead(502);
    clientRes.end('Service Unavailable');
  });
  
  clientReq.pipe(proxyReq);
}

// 创建服务器
const server = http.createServer(proxyRequest);

server.listen(LOCAL_PORT, '127.0.0.1', () => {
  log(`🚀 Ollama代理启动，监听端口 ${LOCAL_PORT}`);
  log(`主服务器: http://${PRIMARY.host}:${PRIMARY.port}`);
  log(`备用服务器: https://${BACKUP.host}`);
});

// 初始检查
checkServer('primary').then(ok => {
  if (!ok) {
    log('⚠️ 主服务器不可用，使用备用服务器');
    currentServer = 'backup';
  }
});