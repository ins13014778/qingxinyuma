import { Injectable } from '@angular/core';

export interface OpenAIAgentsTraceRecord {
  traceId: string;
  traceUrl: string;
  sessionId: string;
  createdAt: string;
  updatedAt: string;
  events: Array<{
    type: string;
    timestamp: string;
    data: any;
  }>;
}

@Injectable({
  providedIn: 'root'
})
export class OpenAIAgentsTraceService {
  startTrace(traceId: string, traceUrl: string, sessionId: string): void {
    const now = new Date().toISOString();
    const record: OpenAIAgentsTraceRecord = {
      traceId,
      traceUrl,
      sessionId,
      createdAt: now,
      updatedAt: now,
      events: [],
    };
    this.writeRecord(record);
  }

  appendEvent(traceId: string, event: any): void {
    const record = this.getTrace(traceId);
    if (!record) return;
    record.events.push({
      type: event?.type || 'unknown',
      timestamp: new Date().toISOString(),
      data: event,
    });
    record.updatedAt = new Date().toISOString();
    this.writeRecord(record);
  }

  getTrace(traceId: string): OpenAIAgentsTraceRecord | null {
    const filePath = this.getTraceFilePath(traceId);
    if (!filePath || !window['fs']?.existsSync?.(filePath)) {
      return null;
    }
    try {
      const raw = window['fs'].readFileSync(filePath, 'utf8');
      return JSON.parse(raw);
    } catch {
      return null;
    }
  }

  listTraces(limit = 20): OpenAIAgentsTraceRecord[] {
    const dir = this.getTraceDir();
    if (!dir || !window['fs']?.existsSync?.(dir)) {
      return [];
    }

    const files = (window['fs']?.readDirSync?.(dir) || [])
      .filter((entry: any) => entry?._isFile && entry.name.endsWith('.trace.json'))
      .map((entry: any) => window['path'].join(dir, entry.name));

    const records = files.map((filePath: string) => {
      try {
        return JSON.parse(window['fs'].readFileSync(filePath, 'utf8')) as OpenAIAgentsTraceRecord;
      } catch {
        return null;
      }
    }).filter(Boolean) as OpenAIAgentsTraceRecord[];

    return records
      .sort((a, b) => String(b.updatedAt).localeCompare(String(a.updatedAt)))
      .slice(0, limit);
  }

  private writeRecord(record: OpenAIAgentsTraceRecord): void {
    const filePath = this.getTraceFilePath(record.traceId);
    if (!filePath) return;
    const dir = this.getTraceDir();
    if (dir && !window['fs']?.existsSync?.(dir)) {
      window['fs']?.mkdirSync?.(dir, { recursive: true });
    }
    window['fs']?.writeFileSync?.(filePath, JSON.stringify(record, null, 2));
  }

  private getTraceDir(): string {
    const appDataPath = window['path']?.getAppDataPath?.();
    if (!appDataPath) return '';
    return window['path'].join(appDataPath, 'openai-agents', 'traces');
  }

  private getTraceFilePath(traceId: string): string {
    const dir = this.getTraceDir();
    if (!dir) return '';
    return window['path'].join(dir, `${traceId}.trace.json`);
  }
}
