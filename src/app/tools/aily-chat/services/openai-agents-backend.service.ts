import { Injectable } from '@angular/core';
import { AgentCliService } from '../../../services/agent-cli.service';

export interface OpenAIAgentsBackendRequest {
  userInput: string;
  sessionId: string;
  sessionDbPath: string;
  runStatePath: string;
  maxTurns?: number;
  mainAgentInstructions?: string;
  mcpConfigPath?: string;
  builtInAgents?: Array<{
    name: string;
    displayName: string;
    description: string;
    useCases?: string[];
    suggestedContext?: string;
  }>;
  mainTools: Array<{
    name: string;
    description: string;
    input_schema: Record<string, any>;
    requires_approval?: boolean;
  }>;
  schematicTools: Array<{
    name: string;
    description: string;
    input_schema: Record<string, any>;
    requires_approval?: boolean;
  }>;
  modelConfig: {
    apiKey: string;
    baseUrl: string;
    model: string;
  };
  cwd?: string;
  /** Per-agent / global ModelSettings overrides. */
  modelSettings?: {
    temperature?: number;
    maxTokens?: number;
    topP?: number;
    frequencyPenalty?: number;
    presencePenalty?: number;
    toolChoice?: string;
    parallelToolCalls?: boolean;
    reasoning?: Record<string, any>;
  };
  /** OpenAI Hosted Tools configuration. Only effective with Responses API. */
  hostedTools?: {
    webSearch?: {
      contextSize?: 'low' | 'medium' | 'high';
      userLocation?: Record<string, any>;
    };
    fileSearch?: {
      vectorStoreIds: string[];
      maxResults?: number;
    };
    codeInterpreter?: {
      container?: Record<string, any>;
    };
    imageGeneration?: {
      quality?: string;
      size?: string;
    };
    hostedMCP?: Array<{
      toolConfig: Record<string, any>;
      approval?: string;
    }>;
  };
  /** OpenAI Prompts API reference. */
  prompt?: {
    id: string;
    version?: string;
    variables?: Record<string, any>;
  };
  /** Project context for dynamic instructions. */
  projectContext?: {
    projectName?: string;
    boardType?: string;
    recentFiles?: string[];
  };
}

export interface OpenAIAgentsToolCall {
  toolId: string;
  toolName: string;
  rawArgs: string;
  args: any;
}

export interface OpenAIAgentsTurnHandlers {
  onToolCall(call: OpenAIAgentsToolCall): Promise<{ content: string; is_error: boolean }>;
  onChunk?(content: string): void;
  onTraceInfo?(traceId: string, traceUrl: string): void;
  onApprovalRequest?(call: { callId: string; toolName: string; rawArgs: string; args: any }): Promise<{ approved: boolean; reason?: string }>;
  onRunnerEvent?(event: any): void;
  /** Lifecycle hook events (agent start/end, LLM start/end, tool start/end, handoff). */
  onHookEvent?(event: { hook: string; agentName: string; [key: string]: any }): void;
  /** Final aggregated hook metrics emitted at end of run. */
  onHookMetrics?(metrics: Record<string, any>): void;
  /** Info about which hosted tools were activated. */
  onHostedToolsInfo?(tools: string[]): void;
  /** Tool-level guardrail warnings (non-blocking). */
  onToolGuardrailWarning?(event: { toolName: string; reason: string; inputPreview: string }): void;
}

@Injectable({
  providedIn: 'root'
})
export class OpenAIAgentsBackendService {
  private activeStreamId: string | null = null;
  private readonly longRunHeartbeatMs = 60000;

  async runTurn(
    request: OpenAIAgentsBackendRequest,
    handlers: OpenAIAgentsTurnHandlers
  ): Promise<string> {
    const runtime = await this.agentCliService.getPythonRuntime();
    if (!runtime) {
      throw new Error('未检测到可用的 Python 解释器');
    }

    const scriptPath = this.agentCliService.getOpenAIAgentsTurnRunnerPath();
    if (!scriptPath || !window['fs']?.existsSync?.(scriptPath)) {
      throw new Error('未找到 openai-agents turn runner 脚本');
    }

    const requestFile = this.writeTempJson(request);
    const streamId = `oa_agents_${Date.now()}_${Math.random().toString(36).slice(2)}`;
    this.activeStreamId = streamId;
    let stdoutBuffer = '';
    let stderrBuffer = '';
    let finalOutput = '';
    let removeListener: (() => void) | null = null;
    let settled = false;
    let eventChain = Promise.resolve();
    const startedAt = Date.now();
    let heartbeatId: ReturnType<typeof setInterval> | null = null;

    this.writeDebugLog(streamId, [
      '=== RUN START ===',
      `script=${scriptPath}`,
      `cwd=${request.cwd || ''}`,
      `sessionId=${request.sessionId}`,
      `sessionDbPath=${request.sessionDbPath}`,
      `runStatePath=${request.runStatePath}`,
      `mcpConfigPath=${request.mcpConfigPath || ''}`,
      `model=${request.modelConfig?.model || ''}`,
      `baseUrl=${request.modelConfig?.baseUrl || ''}`,
      `mainTools=${request.mainTools?.map(t => t.name).join(',') || ''}`,
      `schematicTools=${request.schematicTools?.map(t => t.name).join(',') || ''}`,
      `builtInAgents=${request.builtInAgents?.map(a => a.name).join(',') || ''}`,
      `userInput=${(request.userInput || '').slice(0, 500)}`,
    ]);

    return new Promise<string>((resolve, reject) => {
      const finish = (error?: Error) => {
        if (settled) return;
        settled = true;
        removeListener?.();
        if (heartbeatId) {
          clearInterval(heartbeatId);
          heartbeatId = null;
        }
        this.removeTempFile(requestFile);
        if (this.activeStreamId === streamId) {
          this.activeStreamId = null;
        }
        this.writeDebugLog(streamId, [
          '=== RUN END ===',
          `durationMs=${Date.now() - startedAt}`,
          `error=${error?.message || ''}`,
          `finalOutput=${finalOutput.slice(0, 2000)}`,
          `stderr=${stderrBuffer.slice(-4000)}`,
        ]);
        if (error) {
          reject(error);
          return;
        }
        resolve(finalOutput.trim());
      };

      const handleLine = async (line: string) => {
        if (!line.trim()) return;

        let event: any;
        try {
          event = JSON.parse(line);
        } catch {
          return;
        }

        if (event.type === 'ModelClientStreamingChunkEvent') {
          const content = typeof event.content === 'string' ? event.content : '';
          finalOutput += content;
          handlers.onChunk?.(content);
          this.writeDebugLog(streamId, [`chunk=${content.slice(0, 500)}`]);
          return;
        }

        if (event.type === 'tool_call_request') {
          let parsedArgs: any = {};
          try {
            parsedArgs = event.tool_args ? JSON.parse(event.tool_args) : {};
          } catch {
            parsedArgs = {};
          }
          const result = await handlers.onToolCall({
            toolId: event.tool_id,
            toolName: event.tool_name,
            rawArgs: event.tool_args || '{}',
            args: parsedArgs,
          });
          await window['cmd'].input(
            streamId,
            JSON.stringify({
              type: 'tool_result',
              tool_id: event.tool_id,
              content: result.content,
              is_error: !!result.is_error,
            }) + '\n'
          );
          return;
        }

        if (event.type === 'trace_info') {
          handlers.onRunnerEvent?.(event);
          handlers.onTraceInfo?.(event.trace_id || '', event.trace_url || '');
          return;
        }

        if (event.type === 'approval_request') {
          handlers.onRunnerEvent?.(event);
          let parsedArgs: any = {};
          try {
            parsedArgs = event.tool_args ? JSON.parse(event.tool_args) : {};
          } catch {
            parsedArgs = {};
          }
          const result = await handlers.onApprovalRequest?.({
            callId: event.call_id,
            toolName: event.tool_name,
            rawArgs: event.tool_args || '{}',
            args: parsedArgs,
          }) || { approved: true };
          await window['cmd'].input(
            streamId,
            JSON.stringify({
              type: 'approval_result',
              call_id: event.call_id,
              approved: !!result.approved,
              reason: result.reason || '',
            }) + '\n'
          );
          return;
        }

        if (event.type === 'hook_event') {
          handlers.onHookEvent?.({
            hook: event.hook || '',
            agentName: event.agent_name || '',
            ...event,
          });
          handlers.onRunnerEvent?.(event);
          return;
        }

        if (event.type === 'hook_metrics') {
          handlers.onHookMetrics?.(event.metrics || {});
          handlers.onRunnerEvent?.(event);
          return;
        }

        if (event.type === 'hosted_tools_info') {
          handlers.onHostedToolsInfo?.(event.tools || []);
          handlers.onRunnerEvent?.(event);
          return;
        }

        if (event.type === 'tool_guardrail_warning') {
          handlers.onToolGuardrailWarning?.({
            toolName: event.tool_name || '',
            reason: event.reason || '',
            inputPreview: event.input_preview || '',
          });
          handlers.onRunnerEvent?.(event);
          return;
        }

        if (
          event.type === 'runner_info' ||
          event.type === 'raw_response_event' ||
          event.type === 'run_item_stream_event' ||
          event.type === 'agent_updated_stream_event' ||
          event.type === 'guardrail_tripwire' ||
          event.type === 'tool_budget_skip' ||
          event.type === 'tool_fast_degrade' ||
          event.type === 'max_turns_exceeded'
        ) {
          handlers.onRunnerEvent?.(event);
          return;
        }

        if (event.type === 'TaskCompleted') {
          this.writeDebugLog(streamId, [`taskCompleted stop_reason=${event.stop_reason || ''}`]);
          finish();
          return;
        }

        if (event.type === 'error') {
          this.writeDebugLog(streamId, [`runnerError=${event.message || ''}`]);
          finish(new Error(event.message || 'OpenAI Agents Python 执行失败'));
        }
      };

      removeListener = window['cmd'].onData(streamId, (data: any) => {
        if (settled) return;

        if (data.type === 'stdout' && data.data) {
          stdoutBuffer += data.data;
          this.writeDebugLog(streamId, [`stdout=${data.data.slice(0, 1000)}`]);
          const lines = stdoutBuffer.split(/\r?\n/);
          stdoutBuffer = lines.pop() || '';
          for (const line of lines) {
            eventChain = eventChain.then(() => handleLine(line));
          }
          return;
        }

        if (data.type === 'stderr' && data.data) {
          stderrBuffer += data.data;
          this.writeDebugLog(streamId, [`stderr=${data.data.slice(0, 1000)}`]);
          return;
        }

        if (data.type === 'error') {
          finish(new Error(data.error || 'OpenAI Agents Python 进程启动失败'));
          return;
        }

        if (data.type === 'close') {
          this.writeDebugLog(streamId, [`processClose code=${data.code ?? 0} signal=${data.signal || ''}`]);
          eventChain.finally(() => {
            if (stdoutBuffer.trim()) {
              handleLine(stdoutBuffer.trim())
                .then(() => {
                  if (!settled) {
                    if ((data.code ?? 0) === 0) finish();
                    else finish(new Error(stderrBuffer || stdoutBuffer || 'OpenAI Agents Python 执行失败'));
                  }
                })
                .catch(error => finish(error instanceof Error ? error : new Error(String(error))));
              return;
            }

            if (!settled) {
              if ((data.code ?? 0) === 0) finish();
              else finish(new Error(stderrBuffer || stdoutBuffer || 'OpenAI Agents Python 执行失败'));
            }
          });
        }
      });

      window['cmd'].run({
        command: runtime.command,
        args: [...runtime.argsPrefix, scriptPath, '--request-file', requestFile],
        cwd: request.cwd,
        streamId,
        closeStdin: false,
      }).then((result: any) => {
        if (!result?.success) {
          finish(new Error(result?.error || 'OpenAI Agents Python 进程启动失败'));
          return;
        }
        heartbeatId = setInterval(() => {
          const elapsedMs = Date.now() - startedAt;
          this.writeDebugLog(streamId, [`heartbeat=runner still active elapsedMs=${elapsedMs}`]);
        }, this.longRunHeartbeatMs);
      }).catch((error: any) => {
        finish(error instanceof Error ? error : new Error(String(error)));
      });
    });
  }

  async cancelCurrentRun(): Promise<void> {
    if (!this.activeStreamId) return;
    try {
      await window['cmd'].kill(this.activeStreamId);
    } catch {
      // ignore
    } finally {
      this.activeStreamId = null;
    }
  }

  private writeTempJson(value: unknown): string {
    const tmpDir = window['os']?.tmpdir?.() || '.';
    const fileName = `aily-openai-agents-turn-${Date.now()}-${Math.random().toString(36).slice(2)}.json`;
    const filePath = window['path'].join(tmpDir, fileName);
    window['fs'].writeFileSync(filePath, JSON.stringify(value, null, 2));
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

  private writeDebugLog(streamId: string, lines: string[]): void {
    try {
      const dir = this.getDebugLogDir();
      if (!window['fs']?.existsSync?.(dir)) {
        window['fs']?.mkdirSync?.(dir, { recursive: true });
      }
      const filePath = window['path'].join(dir, `${streamId}.log`);
      const payload = lines.map(line => `[${new Date().toISOString()}] ${line}`).join('\n') + '\n';
      window['fs']?.appendFileSync?.(filePath, payload);
    } catch {
      // ignore logging failures
    }
  }

  private getDebugLogDir(): string {
    const appDataPath = window['path']?.getAppDataPath?.() || '.';
    return window['path'].join(appDataPath, 'openai-agents', 'logs');
  }

  constructor(
    private agentCliService: AgentCliService,
  ) {}
}
