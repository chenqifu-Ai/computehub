var cp = require('child_process');
var fs = require('fs');

var tests = [];
var results = [];
var startTime = Date.now();

function run(name, cmd, args, expectFail) {
    return new Promise(function(resolve) {
        try {
            var r = cp.execFileSync(cmd, args || [], { encoding: 'utf8', timeout: 60000 });
            results.push({
                name: name,
                status: 'PASS',
                output: r.substring(0, 500),
                time: 0
            });
        } catch (e) {
            var msg = e.message || String(e);
            if (expectFail) {
                results.push({ name: name, status: 'EXPECTED_FAIL', output: msg.substring(0, 200), time: 0 });
            } else {
                results.push({ name: name, status: 'FAIL', output: msg.substring(0, 300), time: 0 });
            }
        }
        resolve();
    });
}

async function runAll() {
    await run('GPU信息', 'nvidia-smi', []);
    await run('磁盘空间', 'wmic', ['logicaldisk', 'get', 'caption,freespace,size']);
    await run('CPU信息', 'wmic', ['cpu', 'get', 'name,numberofcores,numberoflogicalprocessors']);
    await run('操作系统', 'wmic', ['os', 'get', 'caption,version,totalvisiblememorysize,freesphysicalmemory']);
    await run('硬盘信息', 'wmic', ['diskdrive', 'get', 'model,size,mediatype']);
    await run('进程列表', 'tasklist', ['/v', '/FO', 'CSV']);
    await run('网络配置', 'ipconfig', ['/all']);
    await run('用户目录', 'dir', ['C:\\Users']);

    var totalTime = Date.now() - startTime;
    var summary = '\n========== 测试结果汇总 ==========\n';
    var pass = 0, fail = 0, efail = 0;
    for (var i = 0; i < results.length; i++) {
        var r = results[i];
        if (r.status === 'PASS') pass++;
        else if (r.status === 'EXPECTED_FAIL') efail++;
        else fail++;
        summary += '[' + r.status + '] ' + r.name + '\n';
    }
    summary += '\n总计: ' + results.length + ' 项 | 通过: ' + pass + ' | 失败: ' + fail + ' | 预期失败: ' + efail + ' | 耗时: ' + totalTime + 'ms\n';

    fs.writeFileSync('C:\\temp\\result.txt', summary + '\n\n=== 详细输出 ===\n', 'utf8');
    for (var i = 0; i < results.length; i++) {
        var r = results[i];
        fs.writeFileSync('C:\\temp\\result.txt', '--- ' + r.name + ' (' + r.status + ') ---\n' + r.output + '\n\n', 'utf8', {flag: 'a'});
    }
    console.log(summary);
}

runAll();
