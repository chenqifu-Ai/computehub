// disk_query.js — 查询磁盘空间标准脚本
var cp = require('child_process');
var fs = require('fs');

try {
    var r = cp.execFileSync('wmic', ['logicaldisk', 'get', 'caption,freespace,size'], { encoding: 'utf8' });
    fs.writeFileSync('C:\\temp\\result.txt', r, 'utf8');
    console.log('DONE');
} catch (e) {
    fs.writeFileSync('C:\\temp\\result.txt', 'ERROR: ' + e.message, 'utf8');
    console.log('ERROR: ' + e.message);
}
