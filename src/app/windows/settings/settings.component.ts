import { Component, ElementRef, ViewChild } from '@angular/core';
import { SubWindowComponent } from '../../components/sub-window/sub-window.component';
import { NzButtonModule } from 'ng-zorro-antd/button';
import { NzInputModule } from 'ng-zorro-antd/input';
import { FormsModule } from '@angular/forms';
import { CommonModule } from '@angular/common';
import { UiService } from '../../services/ui.service';
import { NzRadioModule } from 'ng-zorro-antd/radio';
import { SettingsService } from '../../services/settings.service';
import { TranslationService } from '../../services/translation.service';
import { ConfigService } from '../../services/config.service';
import { SimplebarAngularModule } from 'simplebar-angular';
import { TranslateModule, TranslateService } from '@ngx-translate/core';
import { NzSwitchModule } from 'ng-zorro-antd/switch';
import { NzSelectModule } from 'ng-zorro-antd/select';
import { NzModalService } from 'ng-zorro-antd/modal';
import { ThemeService, ThemeMode } from '../../services/theme.service';
import { AgentCliBackend, AgentCliInstallSource, AgentCliProvider, AgentCliService, AgentCliStatus } from '../../services/agent-cli.service';
import { NzMessageService } from 'ng-zorro-antd/message';

@Component({
  selector: 'app-settings',
  imports: [
    CommonModule,
    FormsModule,
    SubWindowComponent,
    NzButtonModule,
    NzInputModule,
    NzRadioModule,
    SimplebarAngularModule,
    TranslateModule,
    NzSwitchModule,
    NzSelectModule
  ],
  templateUrl: './settings.component.html',
  styleUrl: './settings.component.scss',
})
export class SettingsComponent {
  @ViewChild('scrollContainer', { static: false }) scrollContainer: ElementRef;

  activeSection = 'SETTINGS.SECTIONS.BASIC'; // 当前活动的部分

  // simplebar 配置选项
  options = {
    autoHide: true,
    scrollbarMinSize: 50
  };

  items = [
    {
      name: 'SETTINGS.SECTIONS.BASIC',
      icon: 'fa-light fa-gear'
    },
    {
      name: 'SETTINGS.SECTIONS.THEME',
      icon: 'fa-light fa-gift'
    },
    // {
    //   name: 'SETTINGS.SECTIONS.COMPILATION',
    //   icon: 'fa-light fa-screwdriver-wrench'
    // },
    {
      name: 'SETTINGS.SECTIONS.BLOCKLY',
      icon: 'fa-light fa-puzzle-piece'
    },
    {
      name: 'SETTINGS.SECTIONS.REPOSITORY',
      icon: 'fa-light fa-globe'
    },
    {
      name: 'SETTINGS.SECTIONS.DEPENDENCIES',
      icon: 'fa-light fa-layer-group'
    },
    {
      name: 'SETTINGS.SECTIONS.AGENT_CLI',
      icon: 'fa-light fa-terminal'
    },
    // {
    //   name: 'SETTINGS.SECTIONS.MCP',
    //   icon: 'fa-light fa-webhook'
    // },
    {
      name: 'SETTINGS.SECTIONS.DEVMODE',
      icon: 'fa-light fa-gear-code'
    },
  ];

  // 用于跟踪安装/卸载状态
  boardOperations = {};

  // 搜索关键字
  boardSearchKeyword: string = '';

  get boardList() {
    return this.settingsService.boardList.concat(
      this.settingsService.toolList,
      this.settingsService.sdkList,
      this.settingsService.compilerList
    );;
  }

  // 过滤后的开发板列表
  get filteredBoardList() {
    if (!this.boardSearchKeyword || this.boardSearchKeyword.trim() === '') {
      return this.boardList;
    }
    const keyword = this.boardSearchKeyword.toLowerCase().trim();
    return this.boardList.filter(board =>
      board.name.toLowerCase().includes(keyword) ||
      (board.version && board.version.toLowerCase().includes(keyword))
    );
  }

  get npmRegistryList() {
    return this.configService.getRegionList();
  }

  get apiServerList() {
    return this.configService.getRegionList();
  }

  // 区域对应的国旗映射
  regionFlags: { [key: string]: string } = {
    'cn': '🇨🇳',
    'eu': '🇪🇺',
    'us': '🇺🇸',
    'jp': '🇯🇵',
    'kr': '🇰🇷',
    'localhost': ''
  };

  // 获取区域列表（仅启用的区域）
  get regionList() {
    return this.configService.getEnabledRegionList();
  }

  // 获取区域对应的国旗
  getRegionFlag(key: string): string {
    return this.regionFlags[key] || '🌐';
  }

  // 当前选择的区域
  get selectedRegion() {
    return this.configData.region || 'cn';
  }

  set selectedRegion(value: string) {
    this.configData.region = value;
  }

  // 切换区域
  async onRegionChange(regionKey: string) {
    // 如果选择的区域和当前区域一样，直接返回
    if (regionKey === this.selectedRegion) {
      return;
    }

    this.selectedRegion = regionKey;
    await this.configService.setRegion(regionKey);
    await this.updateBoardList();
  }

  get langList() {
    return this.translationService.languageList;
  }

  get currentLang() {
    return this.translationService.getSelectedLanguage();
  }

  get configData() {
    return this.configService.data;
  }

  appdata_path: string

  mcpServiceList = []
  agentCliStatuses: Record<AgentCliProvider, AgentCliStatus> = {
    'codex-cli': this.buildEmptyStatus('codex-cli'),
    'claude-code': this.buildEmptyStatus('claude-code'),
  };
  agentCliBusy: Partial<Record<AgentCliProvider, 'detecting' | 'installing' | 'upgrading'>> = {};
  readonly agentCliProviders: AgentCliProvider[] = ['codex-cli', 'claude-code'];
  readonly installSourceOptions: { label: string; value: AgentCliInstallSource }[] = [
    { label: '默认国内', value: 'domestic' },
    { label: '官方', value: 'official' },
    { label: '自定义', value: 'custom' },
  ];

  constructor(
    private uiService: UiService,
    private settingsService: SettingsService,
    private translationService: TranslationService,
    private configService: ConfigService,
    private modal: NzModalService,
    private translateService: TranslateService,
    private themeService: ThemeService,
    private agentCliService: AgentCliService,
    private message: NzMessageService,
  ) {
  }

  async ngOnInit() {
    await this.configService.init();
    this.agentCliService.ensureConfig();
    await this.refreshAgentCliStatuses();
  }

  async ngAfterViewInit() {
    await this.updateBoardList();
  }

  async updateBoardList() {
    const platform = this.configService.data.platform;
    // this.appdata_path = this.configService.data.appdata_path[platform].replace('%HOMEPATH%', window['path'].getUserHome());
    this.appdata_path = window['path'].getAppDataPath();
    // 使用当前区域的仓库地址
    const npmRegistry = this.configService.getCurrentNpmRegistry();
    // this.settingsService.getBoardList(this.appdata_path, npmRegistry);
    this.settingsService.getToolList(this.appdata_path, npmRegistry);
    this.settingsService.getSdkList(this.appdata_path, npmRegistry);
    this.settingsService.getCompilerList(this.appdata_path, npmRegistry);
  }

  get agentCliConfig() {
    this.agentCliService.ensureConfig();
    return this.configData.agentCli;
  }

  get currentAgentBackend(): AgentCliBackend {
    return this.agentCliConfig.backend || 'custom-model';
  }

  async onAgentCliSourceChange(value: AgentCliInstallSource) {
    this.agentCliConfig.installSource = value;
    this.configService.save();
  }

  async onAgentCliCustomRegistryChange(value: string) {
    this.agentCliConfig.customRegistry = value;
    this.configService.save();
  }

  async onAgentCliBackendChange(value: AgentCliBackend) {
    this.agentCliConfig.backend = value;
    this.configService.save();
  }

  async refreshAgentCliStatuses() {
    const statuses = await this.agentCliService.detectAll();
    this.agentCliStatuses = statuses;
  }

  getAgentCliLabel(provider: AgentCliProvider): string {
    return this.agentCliService.getProviderLabel(provider);
  }

  getAgentCliResolvedRegistry(): string {
    return this.agentCliService.getResolvedRegistry();
  }

  async detectAgentCli(provider: AgentCliProvider) {
    this.agentCliBusy[provider] = 'detecting';
    try {
      this.agentCliStatuses[provider] = await this.agentCliService.detectProvider(provider);
    } finally {
      delete this.agentCliBusy[provider];
    }
  }

  async installAgentCli(provider: AgentCliProvider) {
    if (this.agentCliStatuses[provider]?.installed) {
      this.message.info(`${this.getAgentCliLabel(provider)} 已安装，无需重复安装`);
      return;
    }
    this.agentCliBusy[provider] = 'installing';
    try {
      this.agentCliStatuses[provider] = await this.agentCliService.installProvider(provider);
      this.message.success(`${this.getAgentCliLabel(provider)} 安装成功`);
    } catch (error: any) {
      this.message.error(error?.message || `${this.getAgentCliLabel(provider)} 安装失败`);
    } finally {
      delete this.agentCliBusy[provider];
    }
  }

  async upgradeAgentCli(provider: AgentCliProvider) {
    this.agentCliBusy[provider] = 'upgrading';
    try {
      this.agentCliStatuses[provider] = await this.agentCliService.upgradeProvider(provider);
      this.message.success(`${this.getAgentCliLabel(provider)} 升级成功`);
    } catch (error: any) {
      this.message.error(error?.message || `${this.getAgentCliLabel(provider)} 升级失败`);
    } finally {
      delete this.agentCliBusy[provider];
    }
  }

  private buildEmptyStatus(provider: AgentCliProvider): AgentCliStatus {
    const label = provider === 'codex-cli' ? 'Codex CLI' : 'Claude Code';
    const commandName = provider === 'codex-cli' ? 'codex' : 'claude';
    const packageName = provider === 'codex-cli' ? '@openai/codex' : '@anthropic-ai/claude-code';
    return {
      provider,
      installed: false,
      version: '',
      commandPath: '',
      packageName,
      commandName,
      installCommand: '',
      upgradeCommand: '',
      error: '',
      lastCheckedAt: '',
    };
  }

  selectLang(lang) {
    this.translationService.setLanguage(lang.code);
    window['ipcRenderer'].send('setting-changed', { action: 'language-changed', data: lang.code });
  }

  // 使用锚点滚动到指定部分
  scrollToSection(item) {
    this.activeSection = item.name;
    const element = document.getElementById(item.name);
    if (element && this.scrollContainer) {
      // 针对simplebar调整滚动方法
      const simplebarInstance = this.scrollContainer['SimpleBar'];
      if (simplebarInstance) {
        simplebarInstance.getScrollElement().scrollTo({
          top: element.offsetTop - 12,
          behavior: 'smooth'
        });
      }
    }
  }

  // 监听滚动事件以更新活动菜单项
  onScroll() {
    const sections = document.querySelectorAll('.section');
    let scrollElement;

    // 获取simplebar的滚动元素
    const simplebarInstance = this.scrollContainer['SimpleBar'];
    if (simplebarInstance) {
      scrollElement = simplebarInstance.getScrollElement();
    } else {
      return;
    }

    const scrollPosition = scrollElement.scrollTop;

    sections.forEach((section: HTMLElement) => {
      const sectionTop = section.offsetTop;
      const sectionHeight = section.offsetHeight;

      if (scrollPosition >= sectionTop - 50 &&
        scrollPosition < sectionTop + sectionHeight - 50) {
        this.activeSection = section.id.replace('section-', '');
      }
    });
  }

  cancel() {
    this.uiService.closeWindow();
  }

  apply() {
    // 保存到config.json，如有需要立即加载的，再加载
    this.configService.save();
    window['ipcRenderer'].send('setting-changed', { action: 'devmode-changed', data: this.configData.devmode });
    // 保存完毕后关闭窗口
    this.uiService.closeWindow();
  }

  onThemeChange(value: string) {
    const mode: ThemeMode = value === 'light' ? 'light' : 'dark';
    this.themeService.setTheme(mode);
    window['ipcRenderer'].send('setting-changed', { action: 'theme-changed', data: mode });
  }

  async uninstall(board) {
    this.boardOperations[board.name] = { status: 'loading' };
    const result = await this.settingsService.uninstall(board)
    if (result === 'success') {
      board.installed = false;
    }
    else if (result === 'failed') {
      this.boardOperations[board.name] = { status: 'failed' };
    }
  }

  async install(board) {
    this.boardOperations[board.name] = { status: 'loading' };
    const result = await this.settingsService.install(board)
    if (result === 'success') {
      board.installed = true;
    }
    else if (result === 'failed') {
      this.boardOperations[board.name] = { status: 'failed' };
    }
  }

  onDevModeChange() {
    // this.configData.devmode = this.configData.devmode;
  }

  // 搜索框变化处理
  onBoardSearchChange() {
    // 搜索逻辑已通过 filteredBoardList getter 实现
    // 这里可以添加额外的处理逻辑，如防抖等
  }
}
