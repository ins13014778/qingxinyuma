import { Injectable } from '@angular/core';
import { Subject } from 'rxjs';

export type LogLevel = 'info' | 'warn' | 'error';

export type LogCategory =
  | 'request'       // 用户发送消息
  | 'response'      // AI 最终回复
  | 'tool_call'     // 工具调用请求
  | 'tool_result'   // 工具调用结果
  | 'error'         // 错误
  | 'handoff'       // Agent 委派
  | 'guardrail'     // 安全护栏
  | 'hook'          // 生命周期事件
  | 'general';      // 通用

@Injectable({
  providedIn: 'root'
})
export class LogService {

  list: LogOptions[] = [];

  stateSubject = new Subject<LogOptions>();

  private readonly MAX_LOG_SIZE = 10000;
  // 超出此阈值才触发清理，避免每条都执行清理，每 500 条触发一次
  private readonly CLEANUP_THRESHOLD = this.MAX_LOG_SIZE + 500;

  constructor() { }

  /**
   * 使用提供的选项更新日志状态。
   * @param opts - 要更新和发送的日志选项。
   */
  update(opts: LogOptions) {
    // 过滤掉无效的日志条目
    if (!opts.title && !opts.detail) return;
    if (opts.title === 'undefined') opts.title = '';
    if (opts.detail === 'undefined') opts.detail = '';

    opts['timestamp'] = Date.now();
    this.list.push(opts);
    if (this.list.length > this.CLEANUP_THRESHOLD) {
      this.list.splice(0, this.list.length - this.MAX_LOG_SIZE);
    }
    this.stateSubject.next(opts);
  }

  /**
   * AI 全链路日志 — 同时写入内存列表（日志面板）和 Electron 文件（持久化）。
   */
  aiLog(opts: {
    level: LogLevel;
    category: LogCategory;
    title: string;
    detail?: string;
    metadata?: Record<string, any>;
  }) {
    const entry: LogOptions = {
      title: `[${opts.category.toUpperCase()}] ${opts.title}`,
      detail: opts.detail,
      state: opts.level === 'error' ? 'error' : opts.level === 'warn' ? 'warn' : 'info',
      level: opts.level,
      category: opts.category,
      metadata: opts.metadata,
      timestamp: Date.now(),
    };

    // 写入内存列表（日志面板）
    this.list.push(entry);
    if (this.list.length > this.CLEANUP_THRESHOLD) {
      this.list.splice(0, this.list.length - this.MAX_LOG_SIZE);
    }
    this.stateSubject.next(entry);

    // 同步写入 Electron 持久化文件
    try {
      const tag = `[${opts.category.toUpperCase()}]`;
      const text = `${tag} ${opts.title}${opts.detail ? ' | ' + opts.detail.slice(0, 500) : ''}`;
      if (opts.level === 'error') {
        window['log']?.error?.(text);
      } else if (opts.level === 'warn') {
        window['log']?.warn?.(text);
      } else {
        window['log']?.info?.(text);
      }
    } catch { /* 忽略 — Electron 不可用时降级为内存日志 */ }
  }

  clear() {
    this.list = [];
  }
}

export interface LogOptions {
  id?: number;
  title?: string;
  detail?: string;
  state?: string;
  timestamp?: number;
  /** 日志级别 */
  level?: LogLevel;
  /** AI 日志分类 */
  category?: LogCategory;
  /** 附加结构化数据 */
  metadata?: Record<string, any>;
}
