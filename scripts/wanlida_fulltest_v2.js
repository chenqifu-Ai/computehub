var cp = require('child_process');
var fs = require('fs');
var path = require('path');

var results = [];
var startTime = Date.now();

function run(name, cmd, args) {
    try {
        var r = cp.execFileSync(cmd, args || [], { encoding: 'utf8', timeout: 60000 });
        results.push({ name: name, status: 'PASS', output: r.substring(0, 500), time: 0 });
    } catch (e) {
        var msg = e.message || String(e);
        if (e.code === 'ENOENT') {
            results.push({ name: name, status: 'SKIP(cmd内置)', output: 'cmd.exe 内置命令，需通过 cmd /C 调用，跳过', time: 0 });
        } else {
            results.push({ name: name, status: 'FAIL', output: msg.substring(0, 300), time: 0 });
        }
    }
}

// 全部测试
run('GPU信息', 'nvidia-smi', []);
run('磁盘空间', 'wmic', ['logicaldisk', 'get', 'caption,freespace,size']);
run('CPU信息', 'wmic', ['cpu', 'get', 'name,numberofcores,numberoflogicalprocessors']);
run('操作系统', 'wmic', ['os', 'get', 'caption,version,totalvisiblememorysize,freesphysicalmemory']);
run('硬盘信息', 'wmic', ['diskdrive', 'get', 'model,size,mediatype']);
run('进程列表', 'tasklist', ['/v', '/FO', 'CSV']);
run('网络配置', 'ipconfig', ['/all']);
run('用户目录', 'cmd', ['/C', 'dir', 'C:\\Users']);

var totalTime = Date.now() - startTime;
var summary = '\n========== wanlida-opc01 全功能测试结果 ==========\n';
var pass = 0, fail = 0, skip = 0;
for (var i = 0; i < results.length; i++) {
    var r = results[i];
    if (r.status === 'PASS') pass++;
    else if (r.status === 'SKIP(cmd内置)') skip++;
    else fail++;
    summary += '[' + r.status + '] ' + r.name + '\n';
}
summary += '\n总计: ' + results.length + ' 项 | 通过: ' + pass + ' | 跳过: ' + skip + ' | 失败: ' + fail + ' | 总耗时: ' + totalTime + 'ms\n';

// 写入结果文件
fs.writeFileSync('C:\\temp\\fulltest_summary.txt', summary, 'utf8');
fs.writeFileSync('C:\\temp\\fulltest_detail.txt', '', 'utf8');
for (var i = 0; i < results.length; i++) {
    var r = results[i];
    var entry = '--- ' + r.name + ' (' + r.status + ') ---\n' + r.output + '\n\n';
    fs.appendFileSync('C:\\temp\\fulltest_detail.txt', entry, 'utf8');
}

console.log(summary);