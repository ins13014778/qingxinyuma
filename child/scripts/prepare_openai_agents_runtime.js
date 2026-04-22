const fs = require('fs');
const path = require('path');
const { execFileSync } = require('child_process');

const OPENAI_AGENTS_VERSION = '0.14.4';

function run(command, args, options = {}) {
  console.log(`[prepare-openai-agents-runtime] ${command} ${args.join(' ')}`);
  return execFileSync(command, args, {
    stdio: 'inherit',
    ...options,
  });
}

function getPythonInfo() {
  const script = [
    'import json, sys',
    'print(json.dumps({',
    '  "executable": sys.executable,',
    '  "base_prefix": sys.base_prefix,',
    '  "version": sys.version.split()[0]',
    '}))',
  ].join('\n');
  const output = execFileSync('python', ['-c', script], { encoding: 'utf-8' });
  return JSON.parse(output);
}

function ensureDir(dirPath) {
  fs.mkdirSync(dirPath, { recursive: true });
}

function removeDir(dirPath) {
  if (fs.existsSync(dirPath)) {
    fs.rmSync(dirPath, { recursive: true, force: true });
  }
}

function copyFileIfExists(src, dest) {
  if (!fs.existsSync(src)) return;
  ensureDir(path.dirname(dest));
  fs.copyFileSync(src, dest);
}

function copyDirFiltered(src, dest, filterFn) {
  if (!fs.existsSync(src)) return;
  ensureDir(dest);

  for (const entry of fs.readdirSync(src, { withFileTypes: true })) {
    const srcPath = path.join(src, entry.name);
    const destPath = path.join(dest, entry.name);
    if (!filterFn(srcPath, entry)) continue;

    if (entry.isDirectory()) {
      copyDirFiltered(srcPath, destPath, filterFn);
    } else if (entry.isFile()) {
      ensureDir(path.dirname(destPath));
      fs.copyFileSync(srcPath, destPath);
    }
  }
}

function runtimeSmokeTest(runtimeRoot) {
  const runtimeSitePackages = path.join(runtimeRoot, 'Lib', 'site-packages');
  const pythonExe = path.join(runtimeRoot, 'python.exe');
  if (!fs.existsSync(pythonExe) || !fs.existsSync(runtimeSitePackages)) {
    return false;
  }

  try {
    const smokeTest = [
      'import sys',
      'import agents',
      'print(sys.executable)',
      'print(agents.__file__)',
    ].join('\n');

    execFileSync(pythonExe, ['-c', smokeTest], {
      stdio: 'ignore',
      env: {
        ...process.env,
        PYTHONHOME: runtimeRoot,
        PYTHONPATH: runtimeSitePackages,
        PATH: [
          runtimeRoot,
          path.join(runtimeRoot, 'DLLs'),
          path.join(runtimeRoot, 'Library', 'bin'),
          process.env.PATH || '',
        ].join(path.delimiter),
      }
    });
    return true;
  } catch {
    return false;
  }
}

function buildRuntime() {
  if (process.platform !== 'win32') {
    console.log('[prepare-openai-agents-runtime] skip: only prepare bundled runtime on Windows');
    return;
  }

  const pythonInfo = getPythonInfo();
  const pythonRoot = pythonInfo.base_prefix;
  const runtimeRoot = path.resolve(__dirname, '..', 'windows', 'python-runtime');
  const runtimeLib = path.join(runtimeRoot, 'Lib');
  const runtimeSitePackages = path.join(runtimeLib, 'site-packages');

  console.log('[prepare-openai-agents-runtime] source python:', pythonInfo.executable);
  console.log('[prepare-openai-agents-runtime] source root:', pythonRoot);
  console.log('[prepare-openai-agents-runtime] target runtime:', runtimeRoot);

  if (runtimeSmokeTest(runtimeRoot)) {
    console.log('[prepare-openai-agents-runtime] existing bundled runtime is healthy, skip rebuild');
    return;
  }

  removeDir(runtimeRoot);
  ensureDir(runtimeRoot);
  ensureDir(runtimeSitePackages);

  const rootFiles = [
    'python.exe',
    'pythonw.exe',
    'python3.dll',
    'python313.dll',
    'vcruntime140.dll',
    'vcruntime140_1.dll',
    'msvcp140.dll',
    'ucrtbase.dll',
  ];
  for (const file of rootFiles) {
    copyFileIfExists(path.join(pythonRoot, file), path.join(runtimeRoot, file));
  }

  copyDirFiltered(
    path.join(pythonRoot, 'DLLs'),
    path.join(runtimeRoot, 'DLLs'),
    () => true
  );

  copyDirFiltered(
    path.join(pythonRoot, 'Library', 'bin'),
    path.join(runtimeRoot, 'Library', 'bin'),
    () => true
  );

  const excludedTopLevelLibDirs = new Set([
    'site-packages',
    'ensurepip',
    'idlelib',
    'test',
    'tests',
    'tkinter',
    'turtledemo',
    '__pycache__',
    'venv',
  ]);

  copyDirFiltered(
    path.join(pythonRoot, 'Lib'),
    runtimeLib,
    (srcPath, entry) => {
      if (path.dirname(srcPath) === path.join(pythonRoot, 'Lib') && entry.isDirectory()) {
        return !excludedTopLevelLibDirs.has(entry.name);
      }
      return !srcPath.includes(`${path.sep}__pycache__${path.sep}`);
    }
  );

  run('python', [
    '-m',
    'pip',
    'install',
    '--upgrade',
    '--no-cache-dir',
    '--target',
    runtimeSitePackages,
    `openai-agents==${OPENAI_AGENTS_VERSION}`,
  ]);

  const smokeTest = [
    'import sys',
    'print(sys.executable)',
    'import agents',
    'print(agents.__file__)',
  ].join('\n');

  run(path.join(runtimeRoot, 'python.exe'), ['-c', smokeTest], {
    env: {
      ...process.env,
      PYTHONHOME: runtimeRoot,
      PYTHONPATH: runtimeSitePackages,
      PATH: [
        runtimeRoot,
        path.join(runtimeRoot, 'DLLs'),
        path.join(runtimeRoot, 'Library', 'bin'),
        process.env.PATH || '',
      ].join(path.delimiter),
    }
  });

  console.log('[prepare-openai-agents-runtime] bundled runtime ready');
}

buildRuntime();
