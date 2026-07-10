// Check openclaw package bin fields
const pkg = require('C:/Users/Administrator/AppData/Roaming/npm/node_modules/openclaw/package.json');
console.log('BIN:', JSON.stringify(pkg.bin, null, 2));
console.log('MAIN:', pkg.main);
console.log('EXPORTS:', typeof pkg.exports);

// Try to run openclaw directly
const path = require('path');
const npmPrefix = 'C:/Users/Administrator/AppData/Roaming/npm';
const nodeBin = path.join(npmPrefix, 'node');
const pkgDir = 'C:/Users/Administrator/AppData/Roaming/npm/node_modules/openclaw';

// Find the main executable
let cmdPath = path.join(npmPrefix, 'openclaw.cmd');
const fs = require('fs');
if (fs.existsSync(cmdPath)) {
  console.log('CMD EXISTS:', cmdPath);
} else {
  // Try bin directory
  const binDir = path.join(pkgDir, 'bin');
  if (fs.existsSync(binDir)) {
    const files = fs.readdirSync(binDir);
    console.log('BIN FILES:', files.join(', '));
  } else {
    console.log('NO BIN DIR');
  }
}

// Try running via node
const { spawnSync } = require('child_process');
const result = spawnSync('node', [path.join(pkgDir, pkg.main || 'index.js'), '--version'], { timeout: 10000 });
console.log('EXIT:', result.status);
if (result.stdout) console.log('STDOUT:', result.stdout.toString().trim());
if (result.stderr) console.log('STDERR:', result.stderr.toString().trim());
