import { Injectable } from '@angular/core';
import { CmdOutput, CmdService } from './cmd.service';
import { ConfigService } from './config.service';

export type AgentCliProvider = 'codex-cli' | 'claude-code';
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

interface AgentCliDefinition {
  provider: AgentCliProvider;
  label: string;
  packageName: string;
  commandName: string;
  installArgs: string[];
}

interface CommandRunResult {
  code: number;
  stdout: string;
  stderr: string;
}

const DOMESTIC_REGISTRY = 'https://registry.npmmirror.com';
const OFFICIAL_REGISTRY = 'https://registry.npmjs.org';

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
      installArgs: ['install', '-g', '@openai/codex']
    },
    {
      provider: 'claude-code',
      label: 'Claude Code',
      packageName: '@anthropic-ai/claude-code',
      commandName: 'claude',
      installArgs: ['install', '-g', '@anthropic-ai/claude-code']
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

  getResolvedRegistry(): string {
    const source = this.getInstallSource();
    if (source === 'official') return OFFICIAL_REGISTRY;
    if (source === 'custom') {
      const customRegistry = this.getCustomRegistry().trim();
      return customRegistry || DOMESTIC_REGISTRY;
    }
    return DOMESTIC_REGISTRY;
  }

  buildInstallCommand(provider: AgentCliProvider): string {
    const definition = this.getDefinition(provider);
    return this.stringifyCommand('npm', [...definition.installArgs, '--registry', this.getResolvedRegistry()]);
  }

  buildUpgradeCommand(provider: AgentCliProvider): string {
    const definition = this.getDefinition(provider);
    return this.stringifyCommand('npm', ['install', '-g', `${definition.packageName}@latest`, '--registry', this.getResolvedRegistry()]);
  }

  async detectProvider(provider: AgentCliProvider): Promise<AgentCliStatus> {
    const definition = this.getDefinition(provider);
    const resolvedCommandPath = await this.resolveCommandPath(definition.commandName);
    const providerSummary = provider === 'codex-cli' ? this.readCodexProviderSummary() : '';
    const versionResult = resolvedCommandPath
      ? await this.runCommand(resolvedCommandPath, ['--version'])
      : { code: 1, stdout: '', stderr: '未找到可执行命令路径' };
    const installed = !!resolvedCommandPath && versionResult.code === 0 && !!versionResult.stdout.trim();
    const version = installed
      ? versionResult.stdout.split(/\r?\n/).map(line => line.trim()).find(Boolean) || ''
      : '';
    const commandPath = resolvedCommandPath || '';

    return {
      provider,
      installed,
      version,
      commandPath,
      packageName: definition.packageName,
      commandName: definition.commandName,
      installCommand: this.buildInstallCommand(provider),
      upgradeCommand: this.buildUpgradeCommand(provider),
      providerSummary,
      error: installed ? '' : (versionResult.stderr || '未检测到命令'),
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
    const args = [...definition.installArgs, '--registry', this.getResolvedRegistry()];
    const result = await this.runCommand('npm', args);
    if (result.code !== 0) {
      throw new Error(result.stderr || result.stdout || `${definition.label} 安装失败`);
    }
    return this.detectProvider(provider);
  }

  async upgradeProvider(provider: AgentCliProvider): Promise<AgentCliStatus> {
    const definition = this.getDefinition(provider);
    const args = ['install', '-g', `${definition.packageName}@latest`, '--registry', this.getResolvedRegistry()];
    const result = await this.runCommand('npm', args);
    if (result.code !== 0) {
      throw new Error(result.stderr || result.stdout || `${definition.label} 升级失败`);
    }
    return this.detectProvider(provider);
  }

  async executePrompt(provider: AgentCliProvider, prompt: string, cwd?: string): Promise<string> {
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

  private getDefinition(provider: AgentCliProvider): AgentCliDefinition {
    const definition = this.providers.find(item => item.provider === provider);
    if (!definition) {
      throw new Error(`未知的 Agent CLI 提供商: ${provider}`);
    }
    return definition;
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
}
