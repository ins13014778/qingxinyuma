import { Injectable } from '@angular/core';
import { CmdOutput, CmdService } from './cmd.service';
import { ConfigService } from './config.service';

export type AgentCliProvider = 'codex-cli' | 'claude-code' | 'openai-agents-python';
export type AgentCliBackend = 'custom-model' | AgentCliProvider;
export type AgentCliInstallSource = 'domestic' | 'official' | 'custom';

export interface AgentCliStatus {
  provider: AgentCliProvider;
  installed: boolean;
  version: string;
  commandPath: string;
  packageName: string;
  commandName: string;
  installCommand: string;
  upgradeCommand: string;
  providerSummary?: string;
  error?: string;
  lastCheckedAt: string;
}

export interface AgentCliExecutionOptions {
  modelConfig?: {
    apiKey: string;
    baseUrl: string;
    model: string;
  } | null;
}

interface AgentCliDefinition {
  provider: AgentCliProvider;
  label: string;
  packageName: string;
  commandName: string;
  installKind: 'npm' | 'python';
  installArgs?: string[];
}

interface PythonCommandResolution {
  executable: string;
  argsPrefix: string[];
  displayName: string;
  resolvedPath: string;
}

export interface AgentCliPythonRuntime {
  command: string;
  argsPrefix: string[];
  displayName: string;
  resolvedPath: string;
}

interface CommandRunResult {
  code: number;
  stdout: string;
  stderr: string;
}

const DOMESTIC_NPM_REGISTRY = 'https://registry.npmmirror.com';
const OFFICIAL_NPM_REGISTRY = 'https://registry.npmjs.org';
const DOMESTIC_PYPI_INDEX = 'https://pypi.tuna.tsinghua.edu.cn/simple';
const OFFICIAL_PYPI_INDEX = 'https://pypi.org/simple';

@Injectable({
  providedIn: 'root'
})
export class AgentCliService {
  private readonly providers: AgentCliDefinition[] = [
    {
      provider: 'codex-cli',
      label: 'Codex CLI',
      packageName: '@openai/codex',
      commandName: 'codex',
      installKind: 'npm',
      installArgs: ['install', '-g', '@openai/codex']
    },
    {
      provider: 'claude-code',
      label: 'Claude Code',
      packageName: '@anthropic-ai/claude-code',
      commandName: 'claude',
      installKind: 'npm',
      installArgs: ['install', '-g', '@anthropic-ai/claude-code']
    },
    {
      provider: 'openai-agents-python',
      label: 'OpenAI Agents Python',
      packageName: 'openai-agents',
      commandName: 'python',
      installKind: 'python',
    }
  ];

  constructor(
    private cmdService: CmdService,
    private configService: ConfigService,
  ) {}

  ensureConfig(): void {
    if (!this.configService.data.agentCli) {
      this.configService.data.agentCli = {};
    }
    this.configService.data.agentCli.backend = this.configService.data.agentCli.backend || 'custom-model';
    this.configService.data.agentCli.installSource = this.configService.data.agentCli.installSource || 'domestic';
    this.configService.data.agentCli.customRegistry = this.configService.data.agentCli.customRegistry || '';
  }

  getProviderDefinitions(): AgentCliDefinition[] {
    return [...this.providers];
  }

  getProviderLabel(provider: AgentCliBackend): string {
    if (provider === 'custom-model') return '自定义模型';
    return this.providers.find(item => item.provider === provider)?.label || provider;
  }

  getSelectedBackend(): AgentCliBackend {
    this.ensureConfig();
    return this.configService.data.agentCli.backend as AgentCliBackend;
  }

  setSelectedBackend(backend: AgentCliBackend): void {
    this.ensureConfig();
    this.configService.data.agentCli.backend = backend;
    this.configService.save();
  }

  getInstallSource(): AgentCliInstallSource {
    this.ensureConfig();
    return this.configService.data.agentCli.installSource as AgentCliInstallSource;
  }

  setInstallSource(source: AgentCliInstallSource): void {
    this.ensureConfig();
    this.configService.data.agentCli.installSource = source;
    this.configService.save();
  }

  getCustomRegistry(): string {
    this.ensureConfig();
    return this.configService.data.agentCli.customRegistry || '';
  }

  setCustomRegistry(registry: string): void {
    this.ensureConfig();
    this.configService.data.agentCli.customRegistry = registry.trim();
    this.configService.save();
  }

  getResolvedRegistry(provider: AgentCliProvider = 'codex-cli'): string {
    const definition = this.getDefinition(provider);
    if (definition.installKind === 'python') {
      return this.getResolvedPythonIndex();
    }
    return this.getResolvedNpmRegistry();
  }

  buildInstallCommand(provider: AgentCliProvider): string {
    const definition = this.getDefinition(provider);
    if (definition.installKind === 'python') {
      return this.stringifyCommand(
        'python',
        ['-m', 'pip', 'install', definition.packageName, '--index-url', this.getResolvedRegistry(provider)]
      );
    }
    return this.stringifyCommand('npm', [...(definition.installArgs || []), '--registry', this.getResolvedRegistry(provider)]);
  }

  buildUpgradeCommand(provider: AgentCliProvider): string {
    const definition = this.getDefinition(provider);
    if (definition.installKind === 'python') {
      return this.stringifyCommand(
        'python',
        ['-m', 'pip', 'install', '--upgrade', definition.packageName, '--index-url', this.getResolvedRegistry(provider)]
      );
    }
    return this.stringifyCommand('npm', ['install', '-g', `${definition.packageName}@latest`, '--registry', this.getResolvedRegistry(provider)]);
  }

  async detectProvider(provider: AgentCliProvider): Promise<AgentCliStatus> {
    const definition = this.getDefinition(provider);
    let installed = false;
    let version = '';
    let commandPath = '';
    let error = '';

    if (definition.installKind === 'python') {
      const python = await this.resolvePythonCommand();
      commandPath = python?.resolvedPath || '';

      if (!python) {
        error = '未检测到可用的 Python 解释器';
      } else {
        const versionResult = await this.runCommand(
          python.executable,
          [
            ...python.argsPrefix,
            '-c',
            'from importlib.metadata import version; print(version("openai-agents"))'
          ]
        );
        installed = versionResult.code === 0 && !!versionResult.stdout.trim();
        version = installed
          ? versionResult.stdout.split(/\r?\n/).map(line => line.trim()).find(Boolean) || ''
          : '';
        error = installed ? '' : (versionResult.stderr || versionResult.stdout || '未检测到 openai-agents');
      }
    } else {
      const resolvedCommandPath = await this.resolveCommandPath(definition.commandName);
      commandPath = resolvedCommandPath || '';
      const versionResult = resolvedCommandPath
        ? await this.runCommand(resolvedCommandPath, ['--version'])
        : { code: 1, stdout: '', stderr: '未找到可执行命令路径' };
      installed = !!resolvedCommandPath && versionResult.code === 0 && !!versionResult.stdout.trim();
      version = installed
        ? versionResult.stdout.split(/\r?\n/).map(line => line.trim()).find(Boolean) || ''
        : '';
      error = installed ? '' : (versionResult.stderr || '未检测到命令');
    }

    return {
      provider,
      installed,
      version,
      commandPath,
      packageName: definition.packageName,
      commandName: definition.commandName,
      installCommand: this.buildInstallCommand(provider),
      upgradeCommand: this.buildUpgradeCommand(provider),
      providerSummary: this.getProviderSummary(provider),
      error,
      lastCheckedAt: new Date().toISOString(),
    };
  }

  async detectAll(): Promise<Record<AgentCliProvider, AgentCliStatus>> {
    const results = await Promise.all(this.providers.map(provider => this.detectProvider(provider.provider)));
    return results.reduce((acc, item) => {
      acc[item.provider] = item;
      return acc;
    }, {} as Record<AgentCliProvider, AgentCliStatus>);
  }

  async installProvider(provider: AgentCliProvider): Promise<AgentCliStatus> {
    const definition = this.getDefinition(provider);
    if (definition.installKind === 'python') {
      const python = await this.resolvePythonCommand();
      if (!python) {
        throw new Error('未检测到可用的 Python 解释器');
      }
      const args = [
        ...python.argsPrefix,
        '-m',
        'pip',
        'install',
        definition.packageName,
        '--index-url',
        this.getResolvedRegistry(provider)
      ];
      const result = await this.runCommand(python.executable, args);
      if (result.code !== 0) {
        throw new Error(result.stderr || result.stdout || `${definition.label} 安装失败`);
      }
      return this.detectProvider(provider);
    }

    const args = [...(definition.installArgs || []), '--registry', this.getResolvedRegistry(provider)];
    const result = await this.runCommand('npm', args);
    if (result.code !== 0) {
      throw new Error(result.stderr || result.stdout || `${definition.label} 安装失败`);
    }
    return this.detectProvider(provider);
  }

  async upgradeProvider(provider: AgentCliProvider): Promise<AgentCliStatus> {
    const definition = this.getDefinition(provider);
    if (definition.installKind === 'python') {
      const python = await this.resolvePythonCommand();
      if (!python) {
        throw new Error('未检测到可用的 Python 解释器');
      }
      const args = [
        ...python.argsPrefix,
        '-m',
        'pip',
        'install',
        '--upgrade',
        definition.packageName,
        '--index-url',
        this.getResolvedRegistry(provider)
      ];
      const result = await this.runCommand(python.executable, args);
      if (result.code !== 0) {
        throw new Error(result.stderr || result.stdout || `${definition.label} 升级失败`);
      }
      return this.detectProvider(provider);
    }

    const args = ['install', '-g', `${definition.packageName}@latest`, '--registry', this.getResolvedRegistry(provider)];
    const result = await this.runCommand('npm', args);
    if (result.code !== 0) {
      throw new Error(result.stderr || result.stdout || `${definition.label} 升级失败`);
    }
    return this.detectProvider(provider);
  }

  async executePrompt(
    provider: AgentCliProvider,
    prompt: string,
    cwd?: string,
    options?: AgentCliExecutionOptions
  ): Promise<string> {
    if (provider === 'openai-agents-python') {
      return this.executeOpenAIAgentsPrompt(prompt, cwd, options);
    }

    const definition = this.getDefinition(provider);
    const commandPath = await this.resolveCommandPath(definition.commandName);
    if (!commandPath) {
      throw new Error(`${definition.label} 未安装或命令路径不可用`);
    }
    const args = provider === 'claude-code'
      ? ['-p', prompt, '--output-format', 'text']
      : ['-a', 'never', 'exec', '--skip-git-repo-check', prompt];
    const result = await Promise.race([
      this.runCommand(commandPath, args, cwd),
      new Promise<CommandRunResult>((_, reject) =>
        setTimeout(() => reject(new Error(`${definition.label} 执行超时，请检查登录状态或命令参数`)), 90000)
      )
    ]);
    if (result.code !== 0) {
      throw new Error(result.stderr || result.stdout || `${definition.label} 执行失败`);
    }
    return result.stdout.trim() || '命令已执行，但没有返回文本输出。';
  }

  async getPythonRuntime(): Promise<AgentCliPythonRuntime | null> {
    const runtime = await this.resolvePythonCommand();
    if (!runtime) return null;
    return {
      command: runtime.executable,
      argsPrefix: runtime.argsPrefix,
      displayName: runtime.displayName,
      resolvedPath: runtime.resolvedPath,
    };
  }

  getOpenAIAgentsTurnRunnerPath(): string {
    const childPath = window['path']?.getAilyChildPath?.();
    if (childPath) {
      return window['path'].join(childPath, 'scripts', 'openai_agents_turn_runner.py');
    }

    const electronPath = window['path']?.getElectronPath?.();
    if (electronPath) {
      return window['path'].resolve(electronPath, '..', 'child', 'scripts', 'openai_agents_turn_runner.py');
    }

    return '';
  }

  private async executeOpenAIAgentsPrompt(
    prompt: string,
    cwd?: string,
    options?: AgentCliExecutionOptions
  ): Promise<string> {
    const python = await this.resolvePythonCommand();
    if (!python) {
      throw new Error('未检测到可用的 Python 解释器');
    }

    const scriptPath = this.getOpenAIAgentsRunnerPath();
    if (!scriptPath || !window['fs']?.existsSync?.(scriptPath)) {
      throw new Error('未找到 openai-agents Python 运行脚本');
    }

    const promptFile = this.writeTempFile('txt', prompt);
    const configFile = this.writeTempFile('json', JSON.stringify(options?.modelConfig || {}, null, 2));

    try {
      const args = [
        ...python.argsPrefix,
        scriptPath,
        '--prompt-file',
        promptFile,
        '--config-file',
        configFile
      ];
      const result = await Promise.race([
        this.runCommand(python.executable, args, cwd),
        new Promise<CommandRunResult>((_, reject) =>
          setTimeout(() => reject(new Error('OpenAI Agents Python 执行超时，请检查模型配置或网络连接')), 180000)
        )
      ]);
      if (result.code !== 0) {
        throw new Error(result.stderr || result.stdout || 'OpenAI Agents Python 执行失败');
      }
      return result.stdout.trim() || 'OpenAI Agents Python 已执行，但没有返回文本输出。';
    } finally {
      this.removeTempFile(promptFile);
      this.removeTempFile(configFile);
    }
  }

  private getDefinition(provider: AgentCliProvider): AgentCliDefinition {
    const definition = this.providers.find(item => item.provider === provider);
    if (!definition) {
      throw new Error(`未知的 Agent CLI 提供者: ${provider}`);
    }
    return definition;
  }

  private getResolvedNpmRegistry(): string {
    const source = this.getInstallSource();
    if (source === 'official') return OFFICIAL_NPM_REGISTRY;
    if (source === 'custom') {
      const customRegistry = this.getCustomRegistry().trim();
      return customRegistry || DOMESTIC_NPM_REGISTRY;
    }
    return DOMESTIC_NPM_REGISTRY;
  }

  private getResolvedPythonIndex(): string {
    const source = this.getInstallSource();
    if (source === 'official') return OFFICIAL_PYPI_INDEX;
    if (source === 'custom') {
      const customRegistry = this.getCustomRegistry().trim();
      return customRegistry || DOMESTIC_PYPI_INDEX;
    }
    return DOMESTIC_PYPI_INDEX;
  }

  private stringifyCommand(command: string, args: string[]): string {
    return [command, ...args.map(arg => this.quoteArg(arg))].join(' ');
  }

  private quoteArg(value: string): string {
    return /\s/.test(value) ? `"${value.replace(/"/g, '\\"')}"` : value;
  }

  private async resolveCommandPath(commandName: string): Promise<string> {
    const candidates: string[] = [];

    const whereTargets = [`${commandName}.cmd`, `${commandName}.exe`, commandName];
    for (const target of whereTargets) {
      try {
        const result = await this.runCommand('where.exe', [target]);
        if (result.code === 0) {
          const found = result.stdout.split(/\r?\n/).map(line => line.trim()).find(Boolean);
          if (found) {
            return found;
          }
        }
      } catch {
        // ignore and continue fallback detection
      }
    }

    const env = window['process']?.env || {};
    const appData = env['APPDATA'] || '';
    const userProfile = env['USERPROFILE'] || '';
    if (appData) {
      candidates.push(`${appData}\\npm\\${commandName}.cmd`);
      candidates.push(`${appData}\\npm\\${commandName}.exe`);
    }
    if (userProfile) {
      candidates.push(`${userProfile}\\AppData\\Roaming\\npm\\${commandName}.cmd`);
      candidates.push(`${userProfile}\\AppData\\Roaming\\npm\\${commandName}.exe`);
    }

    for (const candidate of candidates) {
      try {
        if (window['path']?.isExists?.(candidate)) {
          return candidate;
        }
      } catch {
        // ignore
      }
    }

    return '';
  }

  private async resolvePythonCommand(): Promise<PythonCommandResolution | null> {
    const bundledPythonPath = window['env']?.get ? await window['env'].get('AILY_PYTHON_PATH') : '';
    if (bundledPythonPath && window['fs']?.existsSync?.(bundledPythonPath)) {
      try {
        const versionResult = await this.runCommand(bundledPythonPath, ['--version']);
        if (versionResult.code === 0) {
          return {
            executable: bundledPythonPath,
            argsPrefix: [],
            displayName: 'bundled-python',
            resolvedPath: bundledPythonPath,
          };
        }
      } catch {
        // continue to fallback detection
      }
    }

    const candidates: Array<Omit<PythonCommandResolution, 'resolvedPath'>> = [
      { executable: 'py', argsPrefix: ['-3'], displayName: 'py -3' },
      { executable: 'python', argsPrefix: [], displayName: 'python' },
      { executable: 'python3', argsPrefix: [], displayName: 'python3' },
    ];

    for (const candidate of candidates) {
      try {
        const versionResult = await this.runCommand(candidate.executable, [...candidate.argsPrefix, '--version']);
        if (versionResult.code === 0) {
          const resolvedPath = await this.resolveCommandPath(candidate.executable);
          return {
            ...candidate,
            resolvedPath: resolvedPath || candidate.displayName,
          };
        }
      } catch {
        // ignore and continue
      }
    }

    return null;
  }

  private async runCommand(command: string, args: string[], cwd?: string): Promise<CommandRunResult> {
    return new Promise<CommandRunResult>((resolve, reject) => {
      let stdout = '';
      let stderr = '';
      const observable = this.cmdService.spawn(command, args, { cwd, closeStdin: true }, true);
      observable.subscribe({
        next: (event: CmdOutput) => {
          if (event.type === 'stdout' && event.data) {
            stdout += event.data;
          } else if (event.type === 'stderr' && event.data) {
            stderr += event.data;
          } else if (event.type === 'close') {
            resolve({
              code: event.code ?? 0,
              stdout: event.stdout ?? stdout,
              stderr: event.stderr ?? stderr,
            });
          } else if (event.type === 'error') {
            reject(new Error(event.error || '命令执行失败'));
          }
        },
        error: reject,
      });
    });
  }

  private readCodexProviderSummary(): string {
    try {
      const home = window['path']?.getUserHome?.();
      if (!home) return '';
      const configPath = window['path'].join(home, '.codex', 'config.toml');
      if (!window['fs']?.existsSync?.(configPath)) return '';
      const raw = window['fs'].readFileSync(configPath, 'utf8') as string;
      const provider = raw.match(/model_provider\s*=\s*["']([^"']+)["']/)?.[1] || '';
      const model = raw.match(/model\s*=\s*["']([^"']+)["']/)?.[1] || '';
      const baseUrl = raw.match(/base_url\s*=\s*["']([^"']+)["']/)?.[1] || '';
      const parts = [];
      if (provider) parts.push(`provider=${provider}`);
      if (model) parts.push(`model=${model}`);
      if (baseUrl) parts.push(`base_url=${baseUrl}`);
      return parts.join(' | ');
    } catch {
      return '';
    }
  }

  private getProviderSummary(provider: AgentCliProvider): string {
    if (provider === 'codex-cli') {
      return this.readCodexProviderSummary();
    }
    if (provider === 'openai-agents-python') {
      return '使用当前已选自定义模型，若未配置则回退到 OPENAI_* 环境变量';
    }
    return '';
  }

  private getOpenAIAgentsRunnerPath(): string {
    const childPath = window['path']?.getAilyChildPath?.();
    if (childPath) {
      return window['path'].join(childPath, 'scripts', 'openai_agents_runner.py');
    }

    const electronPath = window['path']?.getElectronPath?.();
    if (electronPath) {
      return window['path'].resolve(electronPath, '..', 'child', 'scripts', 'openai_agents_runner.py');
    }

    return '';
  }

  private writeTempFile(ext: 'txt' | 'json', content: string): string {
    const tmpDir = window['os']?.tmpdir?.() || '.';
    const fileName = `aily-openai-agents-${Date.now()}-${Math.random().toString(36).slice(2)}.${ext}`;
    const filePath = window['path'].join(tmpDir, fileName);
    window['fs'].writeFileSync(filePath, content);
    return filePath;
  }

  private removeTempFile(filePath: string): void {
    try {
      if (filePath && window['fs']?.existsSync?.(filePath)) {
        window['fs'].unlinkSync(filePath);
      }
    } catch {
      // ignore cleanup errors
    }
  }
}
