// 网关模块测试脚本
console.log('=== OpenClaw网关模块测试 ===');

try {
  // 测试导入网关认证模块
  const auth = require('./dist/gateway/auth.js');
  console.log('✅ auth.js 加载成功');
  console.log('导出对象:', Object.keys(auth).filter(k => !k.startsWith('_')).join(', '));
  
  // 测试导入其他网关模块
  const boot = require('./dist/gateway/boot.js');
  console.log('✅ boot.js 加载成功');
  
  const server = require('./dist/gateway/server/index.js');
  console.log('✅ server/index.js 加载成功');
  
  console.log('\\n🎯 网关核心模块测试通过！');
  
} catch (error) {
  console.error('❌ 网关模块测试失败:', error.message);
  if (error.code === 'MODULE_NOT_FOUND') {
    console.log('缺失依赖:', error.message.split("'")[1]);
  }
}