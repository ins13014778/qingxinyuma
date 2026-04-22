import { Injectable } from '@angular/core';

export interface OpenAIAgentsRunStateEntry {
  sessionId: string;
  filePath: string;
  updatedAt: string;
}

@Injectable({
  providedIn: 'root'
})
export class OpenAIAgentsRunStateService {
  listPending(): OpenAIAgentsRunStateEntry[] {
    const dir = this.getRunStateDir();
    if (!dir || !window['fs']?.existsSync?.(dir)) {
      return [];
    }

    const entries = (window['fs']?.readDirSync?.(dir) || [])
      .filter((entry: any) => entry?._isFile && entry.name.endsWith('.runstate.json'))
      .map((entry: any) => {
        const filePath = window['path'].join(dir, entry.name);
        const stat = window['fs']?.statSync?.(filePath);
        const sessionId = entry.name.replace(/\.runstate\.json$/i, '');
        return {
          sessionId,
          filePath,
          updatedAt: stat?.mtime || '',
        } as OpenAIAgentsRunStateEntry;
      })
      .sort((a: OpenAIAgentsRunStateEntry, b: OpenAIAgentsRunStateEntry) => {
        return String(b.updatedAt).localeCompare(String(a.updatedAt));
      });

    return entries;
  }

  getBySessionId(sessionId: string): OpenAIAgentsRunStateEntry | null {
    return this.listPending().find(item => item.sessionId === sessionId) || null;
  }

  deleteBySessionId(sessionId: string): void {
    const entry = this.getBySessionId(sessionId);
    if (!entry) return;
    try {
      window['fs']?.unlinkSync?.(entry.filePath);
    } catch {
      // ignore
    }
  }

  private getRunStateDir(): string {
    const appDataPath = window['path']?.getAppDataPath?.();
    if (!appDataPath) return '';
    return window['path'].join(appDataPath, 'openai-agents');
  }
}
