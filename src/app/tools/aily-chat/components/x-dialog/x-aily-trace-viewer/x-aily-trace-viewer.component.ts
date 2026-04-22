import { Component, Input, ChangeDetectionStrategy } from '@angular/core';
import { CommonModule } from '@angular/common';
import { AilyHost } from '../../../core/host';

@Component({
  selector: 'x-aily-trace-viewer',
  standalone: true,
  imports: [CommonModule],
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="trace-card">
      <div class="trace-header">
        <i class="fa-light fa-timeline"></i>
        <span class="trace-title">{{ data?.title || 'Trace Viewer' }}</span>
      </div>
      @if (data?.traceId) {
        <div class="trace-meta">Trace ID: {{ data.traceId }}</div>
      }
      @if (data?.events?.length) {
        <div class="trace-events">
          @for (item of data.events; track $index) {
            <div class="trace-event">
              <div class="trace-event-type">{{ item.type }}</div>
              <div class="trace-event-time">{{ item.timestamp }}</div>
            </div>
          }
        </div>
      }
      <div class="trace-actions">
        @if (data?.traceUrl) {
          <button class="trace-btn trace-btn-primary" (click)="openExternal()">打开官方 Trace</button>
        }
      </div>
    </div>
  `,
  styles: [`
    .trace-card {
      border-radius: 8px;
      padding: 12px 14px;
      background: var(--aily-chat-viewer-panel, #1e1e1e);
      border: 1px solid var(--aily-chat-viewer-border-soft, #333333);
      color: var(--aily-chat-viewer-fg, #cccccc);
    }
    .trace-header {
      display: flex;
      align-items: center;
      gap: 8px;
      font-weight: 600;
      margin-bottom: 8px;
    }
    .trace-meta {
      font-size: 12px;
      color: var(--aily-chat-viewer-muted, #999999);
      margin-bottom: 8px;
      word-break: break-all;
    }
    .trace-events {
      display: flex;
      flex-direction: column;
      gap: 6px;
      max-height: 220px;
      overflow: auto;
      margin-bottom: 10px;
    }
    .trace-event {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      font-size: 12px;
      padding: 6px 8px;
      border-radius: 6px;
      background: rgba(255,255,255,0.03);
    }
    .trace-event-type {
      font-weight: 500;
    }
    .trace-event-time {
      color: var(--aily-chat-viewer-muted, #999999);
      white-space: nowrap;
    }
    .trace-actions {
      display: flex;
      gap: 8px;
    }
    .trace-btn {
      border: 1px solid var(--aily-chat-viewer-border, #444444);
      background: transparent;
      color: var(--aily-chat-viewer-fg, #cccccc);
      border-radius: 6px;
      padding: 6px 12px;
      cursor: pointer;
    }
    .trace-btn-primary {
      background: var(--aily-chat-viewer-primary, #1890ff);
      border-color: var(--aily-chat-viewer-primary, #1890ff);
      color: #fff;
    }
  `]
})
export class XAilyTraceViewerComponent {
  @Input() data: any = null;

  openExternal(): void {
    if (this.data?.traceUrl) {
      AilyHost.get().shell?.openByBrowser?.(this.data.traceUrl);
    }
  }
}
