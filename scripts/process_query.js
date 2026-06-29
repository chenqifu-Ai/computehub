// process_query.js — 查询进程列表标准脚本
var cp = require('child_process');
var fs = require('fs');

try {
    var r = cp.execFileSync('tasklist', ['/v', '/FO', 'CSV'], { encoding: 'utf8' });
    fs.writeFileSync('C:\\temp\\result.txt', r, 'utf8');
    console.log('DONE');
} catch (e) {
    fs.writeFileSync('C:\\temp\\result.txt', 'ERROR: ' + e.message, 'utf8');
    console.log('ERROR: ' + e.message);
}
