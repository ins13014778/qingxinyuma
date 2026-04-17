# Agent CLI Management Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Windows-only local Agent CLI detection, install, source switching, and chat backend selection for Codex CLI and Claude Code without replacing the existing custom-model AI flow.

**Architecture:** Introduce a dedicated `AgentCliService` for CLI detection/install/upgrade/execute, store persistent CLI source/backend config in app config, surface management UI in the global settings window, and route chat sends through either the existing model flow or the new local CLI flow based on the selected backend.

**Tech Stack:** Angular, Electron, PowerShell/npm, existing `CmdService`, existing `ConfigService`, existing `AilyChatComponent` / `ChatEngineService`

---

### Task 1: Add persistent Agent CLI config

**Files:**
- Modify: `src/app/services/config.service.ts`

- [ ] Add `agentCli` config shape for backend, install source, and custom registry.
- [ ] Ensure defaults are available when older config files do not contain this section.
- [ ] Keep persistence compatible with existing `config.json` save/load flow.

### Task 2: Create local CLI management service

**Files:**
- Create: `src/app/services/agent-cli.service.ts`
- Modify: `src/app/services/cmd.service.ts` (only if a helper is needed)

- [ ] Add provider definitions for `codex-cli` and `claude-code`.
- [ ] Implement Windows detection by checking command availability, version, and resolved path.
- [ ] Implement install/upgrade commands with three source modes: domestic default, official, custom.
- [ ] Implement non-interactive prompt execution for both providers.

### Task 3: Add settings UI for CLI management

**Files:**
- Modify: `src/app/windows/settings/settings.component.ts`
- Modify: `src/app/windows/settings/settings.component.html`

- [ ] Add a new settings section for Agent CLI management.
- [ ] Show source selector, custom registry input, status cards, detect/install/upgrade actions.
- [ ] Prevent repeated install when the CLI is already detected.

### Task 4: Add chat backend switching

**Files:**
- Modify: `src/app/tools/aily-chat/aily-chat.component.ts`
- Modify: `src/app/tools/aily-chat/aily-chat.component.html`
- Modify: `src/app/tools/aily-chat/services/chat-engine.service.ts`

- [ ] Add backend selector UI with `custom-model`, `codex-cli`, and `claude-code`.
- [ ] Preserve the current custom-model path as default/fallback.
- [ ] Route user sends to the local CLI service when a CLI backend is selected.
- [ ] Show friendly errors when the selected CLI is not installed.

### Task 5: Verify and package

**Files:**
- Modify: none

- [ ] Run `npm run build`
- [ ] Confirm the installer is generated under `dist/aily-blockly`
- [ ] Summarize any remaining warnings separately from blocking errors
