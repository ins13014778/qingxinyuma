# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

青芯驭码 (qingxinyuma / "aily blockly") is an Electron + Angular 19 desktop IDE for visual/block-based programming targeting embedded hardware (Arduino-family boards, ESP32, STM32, nRF5). It bundles a Blockly editor, a Monaco-based code editor, serial tools, a simulator, an AI chat assistant, model-training/deploy pipelines, and an integrated builder toolchain. Primary deployment target is Windows; macOS/Linux packaging configs exist but are secondary.

Project files use the custom `.abi` extension (registered as a file association). The custom URL protocol `ailyblockly://` is used for OAuth callbacks.

## Common Commands

Dependencies must be installed in **two locations** — the root (Angular) and `electron/` (native/runtime modules shipped with the app). Skipping the second causes `Cannot find module 'electron-win-state'` and similar runtime errors in packaged builds.

```powershell
# Install (both layers required)
npm install
cd electron && npm install && cd ..

# Dev: Angular dev server + Electron shell together
npm run electron            # concurrently runs `ng serve` and waits on tcp:4200 before launching Electron

# Angular-only watch build (no Electron)
npm run watch

# Production build + Windows installer (output in dist/aily-blockly/)
npm run build               # runs `ng build --base-href ./` then `electron-builder build`

# macOS builds
npm run build:mac           # arm64 + x64
npm run build:mac:universal

# Unit tests (Karma + Jasmine — `skipTests: true` is set in schematics, so most components have no .spec)
npm test                    # equivalent to `ng test`
# Single-file test
npx ng test --include='**/auth.service.spec.ts'
```

Windows packaging requires **Developer Mode** enabled and the resources under `child/windows/` (node runtime, 7zip, aily-builder) — see `develop.md` for the unpack steps.

## High-Level Architecture

### Two-process split

- **Angular renderer** (`src/app/`) — Angular 19 standalone-component app, routing via `provideRouter(routes, withHashLocation())`. All feature pages are lazy-loaded via `loadComponent`. Styling uses ng-zorro-antd (dark theme default) + SCSS.
- **Electron main** (`electron/main.js` + siblings) — owns all native capabilities: serial ports, PTY terminals (`@lydell/node-pty`), filesystem, npm subprocess, probe-rs debugger, ripgrep, MCP (Model Context Protocol) integration, OAuth instance coordination, auto-updater. Each concern is factored into its own module (`serial.js`, `terminal.js`, `npm.js`, `mcp.js`, `probe-rs.js`, `updater.js`, `window.js`, `tools.js`, `upload.js`, `cmd.js`, `notification.js`).
- **Preload bridge** (`electron/preload.js`) — contextBridge exposes a single `window.electronAPI` object covering `ipcRenderer`, `path`, `SerialPort`, `platform`, `terminal`, etc. Renderer code never imports `electron` directly; it always goes through `window.electronAPI`.

### Renderer structure (`src/app/`)

- `main-window/` — root shell component that hosts the primary routed views (guide, project-new, playground, blockly-editor, code-editor).
- `pages/` — top-level routes inside the main window (`guide`, `project-new`, `playground`).
- `editors/` — the three editing surfaces:
  - `blockly-editor/` — Blockly workspace. Subdivided into `components/`, `tools/` (e.g. `code-viewer`), and a local `services/` folder (`blockly.service`, `builder.service`, `history.service`, `project.service`, `uploader.service`, `bitmap-upload.service`). Custom blocks and plugins live under `src/app/blockly/` (see `develop.md` §相关目录).
  - `code-editor/` — Monaco-based text editor. Monaco assets are copied from `node_modules/monaco-editor/min/vs` into `/assets/vs` by the Angular build.
  - `graph-editor/` — node/graph-style editor.
- `windows/` — secondary Electron windows opened via routes (`settings`, `about`, `project-new`, `iframe`, `model-deploy/*`, `model-train/*`). These are rendered by the same Angular app but addressed by hash route and opened as new BrowserWindows.
- `tools/` — feature surfaces that can be opened as panels or sub-windows: `aily-chat` (AI assistant), `serial-monitor`, `simulator`, `terminal`, `model-store`, `app-store`, `cloud-space`, `history-version`, `log`, `user-center`, `data-chart`.
- `services/` — app-wide Angular services. Many are thin wrappers over `window.electronAPI` IPC (`electron.service`, `serial.service`, `cmd.service`, `terminal`/PTY calls, `npm.service`, `builder.service`, `uploader.service`, `esptool-py.service`, `probe-rs.service`). Cross-cutting services include `config.service`, `project.service`, `workflow.service`, `agent-cli.service`, `background-agent.service`, `onboarding.service`, `theme.service`, `translation.service`, `notice.service`, `ui.service`, `update.service`, `auth.service` (the only service with a `.spec.ts`).
- `configs/` — static configuration objects imported at runtime: `ai-config.ts`, `api.config.ts`, `board.config.ts`, `menu.config.ts`, `tool.config.ts`, per-MCU configs (`esp32.config.ts`, `nrf5.config.ts`, `stm32.config.ts`), `feature-flags.ts`, `onboarding.config.ts`.
- `interceptors/` — HTTP interceptors registered via `withInterceptors([authInterceptor, retryInterceptor])` in `app.config.ts`.
- `components/` — shared UI widgets (`aily-blockly`, `aily-coding`, `base-dialog`, `login`, `menu`, `notification`, `onboarding`, `sub-window`, `tool-container`, etc.).
- `workers/`, `func/`, `utils/`, `types/` — Web Workers, pure functions, helpers, shared TypeScript types.

### Runtime resources

- `child/` ships with the installer and contains **out-of-process tooling**: a bundled Node runtime (`child/node/`), 7-Zip binaries, and `aily-builder` (the in-house fast compiler). The NSIS installer extracts `child/node-v22.*-win-x64.7z` into `child/node` on install (see `build/installer.nsh`). The Electron main exposes paths via env vars `AILY_CHILD_PATH`, `AILY_BUILDER_PATH`, `AILY_BUILDER_BUILD_PATH`, `AILY_APPDATA_PATH`, consumed through `preload.js` `path.*` helpers. `child/scripts/` is copied as `extraResources` into the packaged app.
- `public/` — static assets copied verbatim into the build. Includes `public/icon.ico` (all platforms reference it), `public/imgs/logo.webp` + `logo-light.webp` (in-app branding), and `public/i18n/{zh_cn,en}/*.json` for translations.
- `build/` — NSIS installer script (`installer.nsh`) and macOS entitlements. The installer also hard-codes old process names (`aily blockly.exe`, `aily-blockly.exe`, etc.) for upgrade cleanup — see `docs/branding-and-icon-guide.md` for the rename checklist.

### Multi-instance + OAuth coordination

`electron/main.js` implements a multi-instance mode that isolates `userData` per instance under `…/instances/<id>/` while keeping a shared `oauth-instances.json` at the original userData root. OAuth callbacks arriving on the `ailyblockly://` protocol are routed back to the originating instance by looking up the state → instance mapping. When modifying auth/window lifecycle code, preserve this shared-file handoff.

### AI + MCP integration

- The renderer's `aily-chat` tool and Monaco code-intelligence feature both talk to configurable AI endpoints — see `docs/code-intelligence-guide.md` for the completion API contract and `src/app/tools/aily-chat/`.
- `electron/mcp.js` implements a Model Context Protocol bridge (`@modelcontextprotocol/sdk`), exposing local tools to AI agents.
- Agent tooling references live under `docs/agent-config-export.md` and `docs/agent-tool-export.json`.

## Project Conventions

- **Standalone components only.** `app.config.ts` uses `provideRouter` / `provideHttpClient` / `provideAnimations`; there is no NgModule (except the legacy `NzModalModule` imported via `importProvidersFrom`). All routes use `loadComponent`, not `loadChildren`.
- **Hash-based routing** (`withHashLocation()`) because Electron loads from `file://`. Sub-windows use the same bundle and open a route like `#/settings`, `#/about`, `#/serial-monitor` in a new BrowserWindow.
- **Schematics skip tests** (`"skipTests": true` for components/directives/services in `angular.json`), so almost nothing has a `.spec.ts`. Only `auth.service.spec.ts` exists currently.
- **Styles**: SCSS with `inlineStyleLanguage: scss`. Global styles import ng-zorro-antd dark theme, animate.css, loaders.css, xterm CSS, cropper CSS. Build warnings about Sass `@import` deprecation are expected and non-blocking.
- **Bundle budgets**: initial warning 500kB / error 5MB, component styles warning 4kB / error 1MB. Production uses `outputHashing: 'all'`.
- **Renaming the app** touches many files — see `docs/branding-and-icon-guide.md`. At minimum update `productName`, `build.win/mac/nsis.artifactName`, `app.setName()` in `electron/main.js`, process-name checks in `electron/window.js` + `build/installer.nsh`, `<title>` in `src/index.html`, and `TITLE` keys in `public/i18n/*/*.json`. Do not change `appId` unless you intend to break upgrade compatibility with installed versions.
- **Do not import `electron` from the renderer.** Go through `window.electronAPI` (typed in `electron/types/`). Add new IPC by declaring the handler in an `electron/*.js` module and exposing it through `preload.js`.
- **Angular change detection** uses `provideZoneChangeDetection({ eventCoalescing: true, runCoalescing: true })` — be aware that events coalesce, so don't rely on per-event CD ticks.

## Key Documentation

- `develop.md` — quick developer setup (zh-CN), including `child/` resource unpack steps for Windows dev.
- `docs/windows-build-deploy.md` — detailed Windows build, packaging, and troubleshooting (the canonical reference for build failures).
- `docs/branding-and-icon-guide.md` — every file that controls the app name / icon / shortcut / process-name / installer — use before any rebrand.
- `docs/code-intelligence-guide.md` — Monaco completion architecture and AI-completion API contract.
- `docs/onboarding.md` — the centralized `OnboardingService` / `OnboardingComponent` pattern and how to add a new guided tour.
- `docs/aily-security-guidelines.md` — project-specific security notes.
- `docs/action.service.README.md` — `ActionService` (command dispatch) reference.
