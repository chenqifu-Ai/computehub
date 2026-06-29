var cp = require('child_process');
var fs = require('fs');

var results = [];
var startTime = Date.now();

function run(name, cmd, args) {
    try {
        var r = cp.execFileSync(cmd, args || [], { encoding: 'utf8', timeout: 60000 });
        results.push({ name: name, status: 'PASS', output: r.substring(0, 500), time: 0 });
    } catch (e) {
        var msg = e.message || String(e);
        if (e.code === 'ENOENT') {
            results.push({ name: name, status: 'SKIP', output: '系统PATH中找不到 ' + cmd + '，需完整路径', time: 0 });
        } else {
            results.push({ name: name, status: 'FAIL', output: msg.substring(0, 400), time: 0 });
        }
    }
}

// 全部测试（使用绝对路径避免 PATH 问题）
run('GPU信息', 'nvidia-smi', []);
run('磁盘空间', 'wmic', ['logicaldisk', 'get', 'caption,freespace,size']);
run('CPU信息', 'wmic', ['cpu', 'get', 'name,numberofcores,numberoflogicalprocessors']);
run('操作系统', 'wmic', ['os', 'get', 'caption,version,totalvisiblememorysize,freesphysicalmemory']);
run('硬盘信息', 'wmic', ['diskdrive', 'get', 'model,size,mediatype']);
run('进程列表', 'tasklist', ['/v', '/FO', 'CSV']);
run('网络配置', 'ipconfig', ['/all']);
run('用户目录', 'C:\\Windows\\System32\\cmd.exe', ['/C', 'dir', 'C:\\Users']);
run('系统环境变量', 'C:\\Windows\\System32\\cmd.exe', ['/C', 'set']);
run('服务列表', 'C:\\Windows\\System32\\cmd.exe', ['/C', 'sc', 'query', 'type=service', 'state=all']);

var totalTime = Date.now() - startTime;
var summary = '\n========== wanlida-opc01 全功能测试结果 v2 ==========\n';
var pass = 0, fail = 0, skip = 0;
for (var i = 0; i < results.length; i++) {
    var r = results[i];
    if (r.status === 'PASS') pass++;
    else if (r.status === 'SKIP') skip++;
    else fail++;
    summary += '[' + r.status + '] ' + r.name + '\n';
}
summary += '\n总计: ' + results.length + ' 项 | 通过: ' + pass + ' | 跳过: ' + skip + ' | 失败: ' + fail + ' | 总耗时: ' + totalTime + 'ms\n';

// 写入文件
fs.writeFileSync('C:\\temp\\fulltest_summary.txt', summary, 'utf8');
fs.appendFileSync('C:\\temp\\fulltest_detail.txt', '', 'utf8');
for (var i = 0; i < results.length; i++) {
    var r = results[i];
    fs.appendFileSync('C:\\temp\\fulltest_detail.txt', '--- ' + r.name + ' (' + r.status + ') ---\n' + r.output + '\n\n', 'utf8');
}

console.log(summary);
