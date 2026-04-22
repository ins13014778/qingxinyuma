import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'x-aily-runstate-viewer',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="rs-card">
      <div class="rs-header">
        <i class="fa-light fa-pause-circle"></i>
        <span class="rs-title">{{ data?.title || '待恢复会话' }}</span>
      </div>
      @if (data?.message) {
        <div class="rs-message">{{ data.message }}</div>
      }
      <div class="rs-actions">
        <button class="rs-btn rs-btn-primary" (click)="resume()">恢复</button>
        <button class="rs-btn" (click)="dismiss()">忽略</button>
      </div>
    </div>
  `,
  styles: [`
    .rs-card {
      border-radius: 8px;
      padding: 12px 14px;
      background: var(--aily-chat-viewer-panel, #1e1e1e);
      border: 1px solid var(--aily-chat-viewer-border-soft, #333333);
      color: var(--aily-chat-viewer-fg, #cccccc);
    }
    .rs-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      margin-bottom: 8px;
    }
    .rs-message {
      font-size: 12px;
      line-height: 1.5;
      color: var(--aily-chat-viewer-muted, #999999);
      white-space: pre-wrap;
      margin-bottom: 10px;
    }
    .rs-actions {
      display: flex;
      gap: 8px;
    }
    .rs-btn {
      border: 1px solid var(--aily-chat-viewer-border, #444444);
      background: transparent;
      color: var(--aily-chat-viewer-fg, #cccccc);
      border-radius: 6px;
      padding: 6px 12px;
      cursor: pointer;
    }
    .rs-btn-primary {
      background: var(--aily-chat-viewer-primary, #1890ff);
      border-color: var(--aily-chat-viewer-primary, #1890ff);
      color: #fff;
    }
  `],
})
export class XAilyRunStateViewerComponent {
  @Input() data: any = null;

  resume(): void {
    document.dispatchEvent(new CustomEvent('aily-task-action', {
      detail: { action: 'resumeRunState', sessionId: this.data?.sessionId }
    }));
  }

  dismiss(): void {
    document.dispatchEvent(new CustomEvent('aily-task-action', {
      detail: { action: 'dismissRunState', sessionId: this.data?.sessionId }
    }));
  }
}
