import { Component, OnInit } from '@angular/core';
import { GUIDE_MENU } from '../../configs/menu.config';
import { UiService } from '../../services/ui.service';
import { ProjectService } from '../../services/project.service';
import { ConfigService } from '../../services/config.service';
import { version } from '../../../../package.json';
import { TranslateModule } from '@ngx-translate/core';
import { Router } from '@angular/router';
import { ElectronService } from '../../services/electron.service';
import { CommonModule } from '@angular/common';
import { OnboardingService } from '../../services/onboarding.service';
import { GUIDE_ONBOARDING_CONFIG } from '../../configs/onboarding.config';
import { AI_CHAT_ENABLED } from '../../configs/feature-flags';

@Component({
  selector: 'app-guide',
  imports: [TranslateModule, CommonModule],
  templateUrl: './guide.component.html',
  styleUrl: './guide.component.scss'
})
export class GuideComponent implements OnInit {
  version = version;
  guideMenu = GUIDE_MENU.filter(item => AI_CHAT_ENABLED || item.data?.data !== 'aily-chat');
  showMenu = true;
  showMore = false;

  get recentlyProjects() {
    return this.projectService.recentlyProjects;
  }

  constructor(
    private uiService: UiService,
    private projectService: ProjectService,
    private router: Router,
    private electronService: ElectronService,
    private configService: ConfigService,
    private onboardingService: OnboardingService
  ) { }

  get wechatQrcodeUrl(): string {
    const resourceUrl = this.configService.getCurrentResourceUrl();
    return `${resourceUrl}/wechat.jpg`;
  }

  get qqQrcodeUrl(): string {
    const resourceUrl = this.configService.getCurrentResourceUrl();
    return `${resourceUrl}/qq.jpg`;
  }

  ngOnInit() {
    this.checkFirstLaunch();
  }

  private checkFirstLaunch() {
    const hasSeenOnboarding = this.configService.data.onboardingCompleted;
    if (!hasSeenOnboarding) {
      setTimeout(() => {
        this.onboardingService.start(GUIDE_ONBOARDING_CONFIG, {
          onClosed: () => this.onOnboardingClosed(),
          onCompleted: () => this.onOnboardingClosed()
        });
      }, 500);
    }
  }

  private onOnboardingClosed() {
    this.configService.data.onboardingCompleted = true;
    this.configService.save();
  }

  onMenuClick(e: any) {
    this.process(e);
  }

  async selectFolder() {
    const folderPath = await window['ipcRenderer'].invoke('select-folder', {
      path: '',
    });
    console.log('选中的文件夹路径：', folderPath);
    return folderPath;
  }

  async openProject() {
    const path = await this.selectFolder();
    if (path) {
      await this.projectService.projectOpen(path);
    }
  }

  async openProjectByPath(data) {
    await this.projectService.projectOpen(data.path);
  }

  removeProject(event: Event, project: any) {
    event.stopPropagation();
    this.projectService.removeRecentlyProject({ path: project.path });
  }

  process(item) {
    switch (item.action) {
      case 'project-new':
        this.router.navigate(['/main/project-new']);
        break;
      case 'project-open':
        this.openProject();
        break;
      case 'browser-open':
        this.electronService.openUrl(item.data.url);
        break;
      case 'playground-open':
        this.router.navigate(['/main/playground']);
        break;
      case 'tool-open':
        this.uiService.turnTool(item.data);
        break;
      default:
        break;
    }
  }

  openUrl(url: string) {
    this.electronService.openUrl(url);
  }

  gotoPlayground() {
    this.router.navigate(['/main/playground']);
  }

  openFeedback() {
    this.uiService.openFeedback();
  }
}
