// gpu_query.js — 查询 GPU 信息标准脚本
var cp = require('child_process');
var fs = require('fs');

try {
    var r = cp.execFileSync('nvidia-smi', { encoding: 'utf8' });
    fs.writeFileSync('C:\\temp\\result.txt', r, 'utf8');
    console.log('OK ' + r.split('\n')[1].trim());
} catch (e) {
    fs.writeFileSync('C:\\temp\\result.txt', 'ERROR: ' + e.message, 'utf8');
    console.log('ERROR: ' + e.message);
}
