# 青芯驭码 · 技术架构详解

> 本文档面向开发者、架构评审与二次开发者，系统性地说明 **青芯驭码 (aily blockly)** 的技术选型、目录组织、进程模型、关键子系统与扩展点。
> 阅读前建议先看一遍 [`README.md`](../README.md) 了解产品定位，再回到本文看“为什么这样设计”。

---

## 一、项目定位

**青芯驭码**是一款面向嵌入式、硬件原型验证与教学场景的 **桌面图形化编程 IDE**。

| 维度 | 说明 |
| --- | --- |
| 目标用户 | 学生、创客、嵌入式教学、硬件原型开发者 |
| 核心能力 | 积木编程 + 代码编辑 + 串口调试 + 固件上传 + AI 助手 + 模型训练/部署 |
| 目标硬件 | Arduino 家族、ESP32/ESP8266、STM32、nRF5 等 |
| 桌面平台 | **Windows 为主**，保留 macOS / Linux 打包配置 |
| 文件格式 | 项目文件扩展名 `.abi`，自定义 URL 协议 `ailyblockly://`（用于 OAuth 回调） |

---

## 二、技术栈总览

```
┌──────────────────────────────────────────────────────────────┐
│                        应用层 (Angular 19)                   │
│ ┌────────────┬────────────┬────────────┬────────────────────┐ │
│ │  Blockly   │   Monaco   │   xterm    │   ng-zorro-antd    │ │
│ │  11.2      │   0.52     │   5.5      │   19 (dark)        │ │
│ └────────────┴────────────┴────────────┴────────────────────┘ │
│ ┌────────────┬────────────┬────────────┬────────────────────┐ │
│ │  Mermaid   │  Konva     │ Lightweight│  Shiki + Marked    │ │
│ │  (流程图)  │  (画布)    │ Charts     │  (Markdown 渲染)   │ │
│ └────────────┴────────────┴────────────┴────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│                    预加载桥 (contextBridge)                  │
│         window.electronAPI ← preload.js (688 行)             │
├──────────────────────────────────────────────────────────────┤
│                       主进程 (Electron 35)                   │
│ ┌─────────┬─────────┬─────────┬─────────┬──────────────────┐  │
│ │ serial  │ node-pty│  npm    │ probe-rs│ electron-builder │  │
│ │ (串口)  │ (PTY)   │ (子进程)│ (烧录)  │ (打包)           │  │
│ └─────────┴─────────┴─────────┴─────────┴──────────────────┘  │
│ ┌─────────┬─────────┬─────────┬─────────────────────────────┐ │
│ │ MCP SDK │esptool-js│ripgrep │ @orama/orama (向量/全文检索)│ │
│ └─────────┴─────────┴─────────┴─────────────────────────────┘ │
├──────────────────────────────────────────────────────────────┤
│                   操作系统资源 (child/)                      │
│     Node 22 · 7zip · aily-builder · clangd · ripgrep         │
└──────────────────────────────────────────────────────────────┘
```

**关键版本锁定**：
- Angular **19.x** · Electron **35.x** · TypeScript **5.6** · Node 运行时 **22.x**
- Blockly **11.2** + 官方扩展（`block-dynamic-connection`、`field-colour-hsv-sliders`、`workspace-minimap`）
- **Zone.js 0.15** + `provideZoneChangeDetection({ eventCoalescing: true, runCoalescing: true })`：开启事件与运行合并以降低变更检测压力。

---

## 三、双进程模型（最重要的一张图）

Electron 的"主进程 (Main) + 渲染进程 (Renderer) + 预加载 (Preload)"三段式是本项目一切架构的基石：

```
       ┌─────────────────────────────────────────────────┐
       │               Electron Main Process             │
       │                  electron/main.js                │
       │   ┌──────────────────────────────────────────┐   │
       │   │ 应用生命周期 · 多实例 · OAuth 路由       │   │
       │   │ IPC 路由表（ipcMain.handle / on）        │   │
       │   └──────────────────────────────────────────┘   │
       │   ┌─────────┬─────────┬─────────┬───────────┐   │
       │   │serial.js│terminal │ npm.js  │ mcp.js    │   │
       │   │ (串口)  │.js(PTY) │ (编译)  │ (AI 协议) │   │
       │   ├─────────┼─────────┼─────────┼───────────┤   │
       │   │probe-rs │upload.js│updater  │window.js  │   │
       │   │(烧录)   │(固件上传│(自动更新│(窗口管理) │   │
       │   └─────────┴─────────┴─────────┴───────────┘   │
       └─────────────────▲───────────────▲───────────────┘
                         │ IPC           │ IPC
                         │               │
       ┌─────────────────┴───────────────┴───────────────┐
       │            Preload (contextBridge)              │
       │               electron/preload.js               │
       │                                                 │
       │   暴露受控的 window.electronAPI 接口：         │
       │     · ipcRenderer（send / on / invoke）        │
       │     · path（路径工具 + 环境变量路径）          │
       │     · SerialPort / os / platform               │
       │     · terminal（PTY 流式数据）                 │
       │     · 剪贴板 / safeStorage / webFrame          │
       └─────────────────▲───────────────────────────────┘
                         │ 仅通过 window.electronAPI
                         │
       ┌─────────────────┴───────────────────────────────┐
       │           Angular Renderer (src/app)            │
       │                                                 │
       │     Router (Hash) → 标准 + 子窗口路由           │
       │     Services → 调用 window.electronAPI          │
       │     Components → Blockly / Monaco / xterm       │
       │                                                 │
       │     严禁 import 'electron'！                    │
       └─────────────────────────────────────────────────┘
```

**硬性约定**：
1. **渲染进程永远不直接 `import 'electron'`**，所有能力必须走 `window.electronAPI`。
2. **新增原生能力 = 三处改动**：`electron/xxx.js` 实现 + `electron/main.js` 注册 IPC 句柄 + `electron/preload.js` 暴露调用入口 + `src/app/types/electron.d.ts` 补类型。
3. **禁止在 preload 暴露 `require` 或整个 `ipcRenderer`**：仅按功能细粒度包装，避免安全面过大。

---

## 四、项目目录结构

```
aily-blockly-main/
├── angular.json                  # Angular CLI 工程配置（含资源拷贝规则）
├── package.json                  # 根依赖 + electron-builder 配置（NSIS / mac / linux）
├── tsconfig*.json                # 三份 tsconfig（app / spec / base）
│
├── src/                          # Angular 渲染端源码
│   ├── index.html                # SPA 壳
│   ├── main.ts                   # Angular 引导入口
│   ├── styles.scss               # 全局样式
│   └── app/
│       ├── app.config.ts         # provideRouter + provideHttpClient + 拦截器
│       ├── app.routes.ts         # 全部路由（懒加载 + 子路由）
│       ├── app.component.*       # 根组件（仅 router-outlet）
│       ├── main-window/          # 主窗口壳
│       ├── pages/                # guide / playground / project-new
│       ├── editors/              # blockly-editor / code-editor / graph-editor
│       ├── windows/              # settings / about / model-train / model-deploy / iframe
│       ├── tools/                # aily-chat / serial-monitor / simulator / terminal ...
│       ├── components/           # 通用 UI 组件（login / menu / onboarding ...）
│       ├── services/             # 全局服务（>30 个）
│       ├── configs/              # 静态配置（板卡 / 菜单 / AI / 功能开关）
│       ├── interceptors/         # HTTP 拦截器（auth / retry）
│       ├── workers/              # Web Worker（model-train.worker.ts）
│       ├── utils/                # 纯工具函数
│       └── types/                # electron.d.ts 等类型声明
│
├── electron/                     # Electron 主进程源码
│   ├── main.js (2229 行)         # 入口：生命周期 / 多实例 / 协议 / OAuth / IPC 注册
│   ├── preload.js (688 行)       # contextBridge → window.electronAPI
│   ├── window.js                 # BrowserWindow 创建与管理
│   ├── serial.js                 # 串口（throttled SerialPort）
│   ├── terminal.js (371 行)      # node-pty 集成 + 流式数据
│   ├── npm.js                    # 受控 npm 子进程
│   ├── cmd.js / tools.js         # 通用子进程封装
│   ├── mcp.js                    # Model Context Protocol 适配
│   ├── probe-rs.js               # STM32/nRF5 烧录与调试
│   ├── upload.js                 # 固件上传（多链路统一入口）
│   ├── updater.js                # electron-updater 封装
│   ├── notification.js           # 系统通知（Win 通知分组）
│   ├── project-lock.js           # 跨实例项目锁
│   ├── platform.js               # isWin32 / isDarwin / isLinux
│   ├── logger.js                 # 结构化日志
│   ├── config.js                 # 主进程配置
│   ├── config/                   # 配置子目录
│   └── node_modules/             # **独立**依赖树（随打包分发）
│
├── child/                        # 随安装包分发的外部运行时
│   ├── windows/                  # Windows 专属：node-v22.*.7z / aily-builder.7z / 7za.exe / rg.exe
│   ├── macos/                    # macOS 专属：7zz / rg / aily-builder
│   └── scripts/                  # 通用脚本
│
├── build/
│   ├── installer.nsh             # NSIS 安装脚本（负责解压 node / aily-builder / 清理旧进程）
│   └── entitlements.mac.plist    # macOS 沙盒权限
│
├── public/                       # 静态资源（原样拷贝到构建产物）
│   ├── icon.ico / icon-512.ico   # 系统图标
│   ├── imgs/logo.webp            # 应用内 Logo
│   ├── i18n/zh_cn/ en/           # 多语言 JSON
│   └── ...
│
├── docs/                         # 项目文档
│   ├── onboarding.md             # 新手引导系统
│   ├── code-intelligence-guide.md# Monaco + AI 补全
│   ├── branding-and-icon-guide.md# 改名/换图指南
│   ├── windows-build-deploy.md   # Windows 打包手册
│   ├── aily-security-guidelines.md
│   ├── action.service.README.md
│   ├── agent-config-export.md
│   └── architecture.md           # ★ 本文
│
└── dist/                         # electron-builder 输出
    └── aily-blockly/
        ├── 青芯驭码-Setup-x.y.z.exe
        ├── win-unpacked/
        └── latest.yml
```

---

## 五、渲染进程架构

### 5.1 Standalone 全家桶

本项目 **不使用 NgModule**，全部采用 Angular 14+ 引入的 Standalone Components：

```typescript
// src/app/app.config.ts
export const appConfig: ApplicationConfig = {
  providers: [
    provideZoneChangeDetection({
      eventCoalescing: true,
      runCoalescing: true
    }),
    provideRouter(routes, withHashLocation()),
    provideTranslateService(),
    provideHttpClient(withInterceptors([authInterceptor, retryInterceptor])),
    provideAnimations(),
    importProvidersFrom(NzModalModule)   // 仅此一个 legacy Module
  ]
};
```

**要点**：
- `withHashLocation()` 是必选项 —— Electron 通过 `file://` 加载 SPA，HTML5 History 模式会导致刷新 404。
- 事件合并 (`eventCoalescing`) 对高频输入（Blockly 拖拽、Monaco 编辑）的性能至关重要。
- 所有 HTTP 请求统一走 **authInterceptor → retryInterceptor** 流水线。

### 5.2 路由结构（Hash-based 双层路由）

```
/#/main/guide                      →  引导页
/#/main/project-new                →  新建项目
/#/main/playground/list            →  示例列表
/#/main/playground/s/:name         →  示例详情
/#/main/blockly-editor             →  ★ 积木编辑器
/#/main/code-editor                →  ★ 代码编辑器

# 下列路由独立打开新 BrowserWindow（同一份 bundle）
/#/settings                        →  设置窗
/#/about                           →  关于窗
/#/serial-monitor                  →  串口监视器
/#/aily-chat                       →  AI 助手
/#/simulator                       →  模拟器
/#/code-viewer                     →  代码预览
/#/iframe                          →  iframe 包装窗
/#/graph-editor                    →  图形编辑器
/#/model-store                     →  模型市场
/#/model-deploy/sscma/:step?       →  模型部署（步骤化）
/#/model-train                     →  模型训练
/#/model-train/vision/classification
/#/model-train/vision/detection
```

**设计亮点**：**单一 Angular bundle，多个 BrowserWindow**。
主进程根据路由决定创建哪种窗口（尺寸、frame、父子关系），渲染进程只负责根据路由渲染对应页面。这样：
- 所有窗口共享一套组件代码，代码复用率极高；
- 子窗口启动速度快（只是 hash 路由跳转）；
- 打包体积不会因为窗口多而膨胀。

### 5.3 服务层（>30 个）

服务按职责分三类：

**① 原生能力桥接层**（本质是 `window.electronAPI` 的类型化包装）：

| 服务 | 职责 | 底层 |
| --- | --- | --- |
| `electron.service` | 通用 IPC 调用统一入口 | ipcRenderer |
| `serial.service` | 串口开闭、收发、节流 | `SerialPort` + throttled buffer |
| `cmd.service` / `cross-platform-cmd.service` | 跨平台命令执行 | child_process |
| `npm.service` | 受控 npm 安装/查询 | npm.js |
| `builder.service` | 调用 aily-builder 编译 | subprocess |
| `uploader.service` / `esploader.service` / `esptool-py.service` | 固件上传三条路径 | serialport / esptool-js / python subprocess |
| `probe-rs.service` | STM32/nRF5 烧录 | probe-rs CLI |

**② 业务领域层**：

| 服务 | 职责 |
| --- | --- |
| `project.service` | 项目生命周期：创建、打开、保存、迁移 |
| `model-project.service` | 模型项目（ML 相关）的专用逻辑 |
| `workflow.service` | 编译→上传→监视器的一条龙流水线 |
| `background-agent.service` | 后台 Agent 任务调度 |
| `agent-cli.service` | Agent CLI 交互（类似 Claude Code 的 Agent） |
| `firmware.service` | 固件元数据、版本匹配 |
| `compile-validation.service` | 编译前置校验 |
| `sscma-command.service` | SSCMA 模型命令集 |
| `connection-graph.service` | 硬件连接关系图 |
| `action.service` | 全局命令分发（见 `docs/action.service.README.md`） |

**③ 平台与 UI 层**：

| 服务 | 职责 |
| --- | --- |
| `config.service` | 用户配置读写（settings.json） |
| `settings.service` | 设置窗 UI 状态 |
| `theme.service` | 深/浅主题切换（ng-zorro-antd 双主题） |
| `translation.service` | ngx-translate 包装 |
| `onboarding.service` | 集中式新手引导（见 `docs/onboarding.md`） |
| `ui.service` | UI 状态（抽屉、弹窗、加载态） |
| `notice.service` | 应用内通知 |
| `log.service` | 结构化日志 |
| `update.service` | 自动更新前端逻辑 |
| `auth.service` | 登录、OAuth、Token 管理（**唯一有 .spec.ts 的服务**） |
| `platform.service` / `iwindow.service` | 平台与窗口判断 |
| `converter.service` | 单位/格式转换 |

### 5.4 功能模块对照表

| 区域 | 位置 | 说明 |
| --- | --- | --- |
| **主窗口壳** | `main-window/` | 承载菜单、侧栏、顶栏、路由出口 |
| **Blockly 编辑器** | `editors/blockly-editor/` | 核心编辑器；内含 `components/`、`tools/code-viewer/`、`services/`（6 个 Blockly 专用服务）、`shortcut.service.ts` |
| **Monaco 代码编辑器** | `editors/code-editor/` | 主题、智能补全、AI 建议（见 §6.2） |
| **图形编辑器** | `editors/graph-editor/` | 节点图式编辑 |
| **AI 助手** | `tools/aily-chat/` | 聊天 UI + tiktoken 计数 + 多轮上下文（assets 含 tiktoken JSON） |
| **串口监视器** | `tools/serial-monitor/` | xterm + 串口 |
| **模拟器** | `tools/simulator/` | 硬件模拟 |
| **应用/模型商店** | `tools/app-store/` · `tools/model-store/` | 包管理 UI |
| **云空间** | `tools/cloud-space/` | 云端项目同步 |
| **历史版本** | `tools/history-version/` | 项目快照 |
| **模型训练** | `windows/model-train/vision-train/classification-train/` · `detection-train/` | 使用 `workers/model-train.worker.ts` 进行 Web Worker 训练 |
| **模型部署** | `windows/model-deploy/sscma-deploy/` | 步骤化向导 |

---

## 六、核心子系统详解

### 6.1 Blockly 可视化编程

**依赖栈**：
```
blockly@11.2.2                            核心
@blockly/block-dynamic-connection@0.7.16  动态连接块（if/elif/else）
@blockly/field-colour-hsv-sliders@5.0.19  HSV 颜色拾取字段
@blockly/workspace-minimap@0.2.16         小地图
```

**集成位置**：`src/app/editors/blockly-editor/`

**目录**：
```
blockly-editor/
├── blockly-editor.component.{ts,html,scss}   # 主组件
├── services/
│   ├── blockly.service.ts      # Blockly workspace 控制
│   ├── builder.service.ts      # 生成代码 → 提交编译
│   ├── history.service.ts      # Undo/Redo + 本地历史
│   ├── project.service.ts      # 积木项目 IO
│   ├── uploader.service.ts     # 直接上传
│   └── bitmap-upload.service.ts# 点阵图上传（字库、图标）
├── tools/code-viewer/          # 代码预览子窗
├── components/                 # 工具栏、属性面板等
└── shortcut.service.ts         # 快捷键
```

**关键机制**：
- **Angular ↔ Blockly 互操作**：Blockly 是命令式 DOM 库，在 Angular 中必须在 `ngAfterViewInit` 注入容器，销毁时调用 `workspace.dispose()`，不能依赖 CD。
- **资源拷贝**：`angular.json` 把 `node_modules/blockly/media/` 拷贝到 `blockly/media`，供 Blockly 运行时加载图标。
- **自定义块**：按 develop.md 约定放在 `src/app/blockly/plugins` 与 `src/app/blockly/custom-field`（目前仓库未内建，扩展时按此组织）。
- **小地图**：通过 `@blockly/workspace-minimap` 注入，悬浮在工作区右下角。

### 6.2 Monaco + 智能补全

详见 [`docs/code-intelligence-guide.md`](./code-intelligence-guide.md)。核心是 **两级补全**：

```
[用户输入]
    │
    ├─► 本地符号补全
    │      · 扫描 Arduino SDK 和库的 .h/.cpp
    │      · 构建符号表（函数/类/变量）
    │      · monaco.languages.registerCompletionItemProvider
    │
    └─► AI 云端补全
           · POST code + 光标位置 + 前后上下文
           · 缓存 30s，Tab 键接受
           · 可配 endpoint / apiKey / model / temperature
```

Monaco 资源通过 `angular.json` 拷贝：
```json
{ "input": "node_modules/monaco-editor/min/vs", "output": "/assets/vs" }
```

**tiktoken** 资源单独拷贝到 `/aily-chat/tiktoken`，用于 AI 助手前端计算 token 数。

### 6.3 串口通信（throttled SerialPort）

**电机**：`serialport@^13`（通过 `@serialport/*` + `@lydell/node-pty`）。

**分层**：
```
渲染层:   serial.service.ts
             ↓ window.electronAPI.SerialPort.{list,create}
预加载层: preload.js 调用 electron/serial.js
             ↓ createThrottledSerialPort
主进程:    serial.js 封装 SerialPort
             · 节流缓冲：避免高频 data 事件淹没 IPC
             · 端口列表：listPorts() 过滤虚拟端口
```

**为什么要节流？** 串口在 115200 波特率下每秒可产生数千次 `data` 事件，直接 `ipcRenderer.send` 会拖垮 IPC 队列。通过 50ms 聚合窗口发送，既保证可视化流畅，又不丢数据。

### 6.4 PTY 终端

**电机**：`@lydell/node-pty@1.1`（预编译 Windows/macOS/Linux 二进制）。

**预加载暴露**（`window.electronAPI.terminal`）：
```
init / getShell / onData / sendInput / sendInputAsync
close / resize / startStream / stopStream
```

**流式模式**的必要性：xterm 显示大量历史日志（编译输出）时，以 DataChannel 方式订阅比 event 方式更可控 —— 渲染端可以随时 `stopStream` 释放反压。

**asarUnpack**：
```json
"asarUnpack": [
  "electron/node_modules/@lydell/**",
  "electron/node_modules/@serialport/**",
  "electron/node_modules/serialport/**"
]
```
含原生 `.node` 模块必须从 asar 解包，否则动态加载会失败。

### 6.5 AI 助手（aily-chat）

位置：`src/app/tools/aily-chat/`

**能力**：
- 多轮对话 UI
- Markdown 渲染（`marked` + `marked-highlight` + `shiki` 代码高亮）
- Mermaid 流程图渲染
- `js-tiktoken` 前端 token 计数（用来在提示框显示成本）
- `@orama/orama` 本地向量/全文检索（用于 RAG 场景）
- `jsonrepair`：修复 LLM 输出中常见的 JSON 损坏
- `penpal`：跨 iframe 通信（当 AI 在 iframe 沙箱里运行）

**配置注入**：`src/app/configs/ai-config.ts`，支持多模型切换（OpenAI 兼容接口 + 自建模型）。

### 6.6 MCP (Model Context Protocol)

**电机**：`@modelcontextprotocol/sdk@^1.25`（主进程）。

**文件**：`electron/mcp.js`（111 行）

**用途**：把本地工具（文件、串口、编译器）作为 MCP tools 暴露给 AI Agent —— Agent 可以"自己决定"调用 `read_file`、`compile`、`upload` 等操作。与 `agent-cli.service` 配合实现 Agent 模式的编程辅助。

### 6.7 编译构建链（aily-builder）

**aily-builder 是自研的快速编译工具**（见 `develop.md`），打包为 7z 压缩包放在 `child/windows/aily-builder-*.7z`，**安装时**由 NSIS 脚本解压到 `child/aily-builder`。

**路径约定**（通过环境变量注入）：
```
AILY_CHILD_PATH           = <app>/child
AILY_BUILDER_PATH         = <app>/child/aily-builder
AILY_BUILDER_BUILD_PATH   = <app>/child/aily-builder/build
AILY_APPDATA_PATH         = AppData 目录
```

**调用链**：`builder.service` → `electron.service.invoke('builder:build')` → `electron/tools.js` → spawn `aily-builder.exe` → 流式输出到 PTY → xterm 显示。

### 6.8 固件上传（三条路径统一抽象）

| 硬件 | 工具 | 服务 | 备注 |
| --- | --- | --- | --- |
| AVR (Arduino Uno/Nano) | avrdude (via aily-builder) | `uploader.service` | 走串口 STK500 |
| ESP32 / ESP8266 | `esptool-js@0.5.7` | `esploader.service` | **WebSerial 原生 JS 实现**，无需 python |
| ESP32 (兼容回退) | Python esptool | `esptool-py.service` | 走 `child/python` |
| STM32 / nRF5 | `probe-rs` | `probe-rs.service` + `electron/probe-rs.js` | JTAG/SWD |

**`esptool-js` 是重大优势**：对用户来说，ESP32 上传无需再装 Python 环境，直接使用浏览器串口 API 在渲染端完成烧录。

### 6.9 模型训练与部署（SSCMA 生态）

- **训练**：`src/app/windows/model-train/vision-train/` 提供图像分类（classification）与检测（detection）两条流水线，底层跑 `src/app/workers/model-train.worker.ts`（Web Worker，避免阻塞 UI）。
- **部署**：`src/app/windows/model-deploy/sscma-deploy/` 是步骤化向导（路由 `sscma/:step`），把训练产物部署到目标硬件。
- **模型商店**：`src/app/tools/model-store/` 提供预训练模型下载。

---

## 七、运行时资源（child/ 目录）

**这是本项目区别于普通 Electron 应用的最大特征**：打包时会把一整套外部工具一起分发。

```
child/
├── windows/
│   ├── node-v22.19.0-win-x64.7z      # Node 运行时（供 npm 子进程）
│   ├── aily-builder-*.7z              # 自研编译器
│   ├── 7za.exe                        # 解压器（启动时自解压用）
│   ├── rg.exe                         # ripgrep（代码搜索）
│   └── clangd/                        # C++ 语言服务
├── macos/
│   └── ...（macOS 对应版本）
└── scripts/                           # 跨平台脚本
```

**为什么要自带 Node？**
- 用户机器上可能没装 Node，或版本错乱。
- 可控版本：避免"在开发者机器能跑、用户那边 Node 18 报错"。
- `child/node/.npmrc` 指向项目私有 npm 源（`dl.yysc.tech` 或类似），下载 Arduino 库包。

**为什么要 7z 压缩？**
- aily-builder 和 Node 加起来几百 MB，用 7z 极限压缩能砍掉 60% 安装包体积。
- 安装时**一次性解压**到 `child/node`、`child/aily-builder`，运行时直接用。

**NSIS 解压逻辑**：在 `build/installer.nsh` 中调用 `7za.exe x ...`。

---

## 八、多实例与 OAuth 协调

**核心诉求**：用户可能同时打开多个项目（多实例），每个实例都可能发起 OAuth 登录，但 OS 只能把 `ailyblockly://` 回调路由给**其中一个**进程。

**解决方案**（见 `electron/main.js` 前 200 行）：

```
用户数据目录 (原始 userData)
├── oauth-instances.json        ← 共享状态文件（进程间握手）
└── instances/
    ├── <pid_a>/                ← 实例 A 的隔离 userData
    │   ├── Cookies
    │   └── ...
    └── <pid_b>/                ← 实例 B 的隔离 userData
        └── ...
```

**握手流程**：

```
1. 实例 A 发起 OAuth，将 { state, pid, userDataPath, ts } 写入 oauth-instances.json
2. 浏览器完成认证 → 系统回调 ailyblockly://callback?state=XYZ
3. OS 把回调路由给任意一个在运行的实例（假设是 B）
4. 实例 B 读 oauth-instances.json，根据 state 找到实例 A 的 pid
5. 实例 B 通过 IPC/文件通知实例 A，或把回调参数写回 oauth-instances.json
6. 实例 A 捕获到回调，完成登录
```

**过期清理**：状态文件里 `ts > 10 分钟` 的记录自动淘汰，防止累积垃圾。

**修改此逻辑时的注意**：
- `oauth-instances.json` 写在**原始** userData 下（实例隔离**前**的路径），不要改到 instance 子目录。
- 不要假设回调一定先打到发起者 —— 永远要做跨实例协调。

---

## 九、打包与分发

### 9.1 electron-builder 配置要点（`package.json` > `build`）

```json
{
  "appId": "blockly.aily.pro",         // 应用唯一 ID（勿轻易改）
  "asar": true,                         // 渲染端代码打包到 app.asar
  "asarUnpack": [...],                  // 含原生模块 (.node) 的部分必须解包
  "protocols": [{ "schemes": ["ailyblockly"] }],
  "files": [
    "package.json",
    { "from": "electron", "to": "electron" },
    { "from": "electron/node_modules", "to": "electron/node_modules" },
    { "from": "dist/aily-blockly/browser", "to": "renderer" }
  ],
  "extraResources": [
    { "from": "child/scripts", "to": "child/scripts" },
    { "from": "public/icon.ico", "to": "icon.ico" },
    { "from": "electron/app-update.yml", "to": "app-update.yml" }
  ],
  "win": {
    "target": "nsis",
    "artifactName": "青芯驭码-${version}.${ext}",
    "fileAssociations": [{ "ext": "abi", "name": "青芯驭码项目" }],
    "extraResources": [
      { "from": "child/windows", "to": "child" }      // Windows 专属
    ]
  },
  "nsis": {
    "oneClick": false,                  // 显示自定义安装向导
    "allowToChangeInstallationDirectory": true,
    "perMachine": true,                 // 要求管理员权限
    "include": "build/installer.nsh",   // 自定义 NSIS 脚本（解压 7z / 关旧进程）
    "deleteAppDataOnUninstall": true
  }
}
```

### 9.2 两条构建命令

```bash
# 1) Angular 构建 → dist/aily-blockly/browser/
#    angular.json 中 "assets" 把 blockly media / monaco-editor / tiktoken / ng-zorro css 一并拷贝
ng build --base-href ./

# 2) electron-builder → dist/aily-blockly/青芯驭码-Setup-x.y.z.exe
electron-builder build
```

合并为：`npm run build`。

### 9.3 --base-href ./ 的必要性

**Electron 通过 `file://` 加载 HTML**，Angular 默认的 `/assets/...` 绝对路径会失败。加 `--base-href ./` 变成相对路径后才能正确加载。

### 9.4 bundle 预算

```
initial           warning 500 KB / error 5 MB
anyComponentStyle warning 4 KB  / error 1 MB
outputHashing     all (生产)
```

Monaco + Blockly + mermaid 让 initial 极易超 500KB，**这些 warning 是预期的**。

### 9.5 平台差异

| 平台 | 图标 | 文件关联 | 特殊资源 |
| --- | --- | --- | --- |
| Windows | `public/icon.ico` | `.abi` | `child/windows/*` |
| macOS | `public/icon-512.ico`（建议改 `.icns`） | `.abi` | `child/macos/*` |
| Linux | `public/icon.ico`（建议单独 `.png`） | `.abi` + `mimeType` | — |

macOS 还支持 `build:mac:universal`（通用二进制 arm64 + x64）。

---

## 十、国际化与主题

### 10.1 i18n

- 引擎：`@ngx-translate/core@16`
- 语言文件：`public/i18n/{zh_cn,en}/*.json`（被 Angular 资源管道拷贝到构建产物）
- 默认语言：通过 `process.env.AILY_SYSTEM_LANG` 主进程注入（默认 `zh-CN`），`preload.js` 暴露为 `window.electronAPI.platform.lang`
- 约定：引导页/对话/菜单全部走翻译键；硬编码字符串需要有 issue 标记

### 10.2 主题

- 基础：ng-zorro-antd 深色主题（`ng-zorro-antd.dark.css` 默认载入）
- 切换：`theme.service` 在 `<body>` 切换 class；另外载入 `ng-zorro-antd.min.css`（浅色）按需启用
- 动画：`animate.css` + Angular `provideAnimations()`
- 图表：`lightweight-charts` 深色默认，图像处理 `konva` + `cropperjs`

---

## 十一、性能与稳定性关键点

| 问题 | 解决方案 | 位置 |
| --- | --- | --- |
| V8 内存不足（大型项目） | `--max-old-space-size=4096` | `main.js`:12 |
| GPU shader cache 持续增长 | `disable-gpu-shader-disk-cache` | `main.js`:13 |
| HTTP cache 无限膨胀 | `disk-cache-size=100MB` | `main.js`:15 |
| 串口事件过载 | 50ms 节流聚合 | `serial.js` |
| Angular 变更检测抖动 | Zone 事件合并 | `app.config.ts` |
| asar 内原生模块加载失败 | `asarUnpack` 解出 .node | `package.json` |
| 多窗口重复加载 Monaco | 统一从 `/assets/vs` 加载，共享缓存 | `angular.json` |
| AI 补全重复请求 | 30 秒本地缓存 | `code-intelligence-guide.md` |

---

## 十二、扩展开发指南

### 12.1 新增一个 IPC 能力（最常见场景）

**目标**：让渲染端能调用 "获取 CPU 信息"。

1. **主进程实现**（新建 `electron/sysinfo.js`）：
   ```js
   const os = require('os');
   function getCpuInfo() { return os.cpus(); }
   module.exports = { getCpuInfo };
   ```
2. **注册 IPC**（在 `electron/main.js`）：
   ```js
   const { getCpuInfo } = require('./sysinfo');
   ipcMain.handle('sysinfo:cpu', () => getCpuInfo());
   ```
3. **暴露到渲染端**（在 `electron/preload.js`）：
   ```js
   sysinfo: {
     getCpu: () => ipcRenderer.invoke('sysinfo:cpu')
   }
   ```
4. **补类型**（在 `src/app/types/electron.d.ts`）：
   ```ts
   interface ElectronAPI {
     sysinfo: { getCpu(): Promise<os.CpuInfo[]>; };
   }
   ```
5. **写服务**（新建 `src/app/services/sysinfo.service.ts`）：
   ```ts
   @Injectable({ providedIn: 'root' })
   export class SysinfoService {
     getCpu() { return window.electronAPI.sysinfo.getCpu(); }
   }
   ```

### 12.2 新增一个子窗

1. 在 `app.routes.ts` 加一条新路由（`loadComponent`）。
2. 在主进程 `window.js` 里加一个 `openXxxWindow()` 函数，创建 BrowserWindow 并 `loadURL(xxx#/your-route)`。
3. 在主进程 `main.js` 注册触发器（通常是菜单或 IPC）。
4. 样式建议复用 `components/sub-window/` 壳组件，自动带 frame / 最小化 / 关闭按钮。

### 12.3 新增一个板卡支持

1. 在 `src/app/configs/` 新建 `yourboard.config.ts`（参考 `esp32.config.ts`）。
2. 把配置注入 `board.config.ts` 聚合表。
3. 如果有新烧录方式，在 `services/` 加一个 `xxx-uploader.service.ts`，并在 `workflow.service` 中根据板卡类型路由到对应上传器。
4. 在 aily-builder 侧新增编译配方（如果编译链不同）。

### 12.4 新增一个 Blockly 插件

1. 按 `develop.md` 约定放到 `src/app/blockly/plugins/<your-plugin>/`。
2. 在 `blockly.service` 的初始化阶段注册。
3. 如果是自定义字段，放到 `src/app/blockly/custom-field/`。
4. 资源（图标/音效）放到 `public/blockly/`，在 `angular.json` 加 `assets` 映射（如不已覆盖）。

### 12.5 修改应用名/图标

**必读**：[`docs/branding-and-icon-guide.md`](./branding-and-icon-guide.md)

最小改动清单：
- `package.json`：`productName`、`build.*.artifactName`、`build.nsis.shortcutName`
- `electron/main.js`：`app.setName(...)` + `AppUserModelId`
- `electron/window.js` + `build/installer.nsh`：旧进程名清理
- `src/index.html`：`<title>`
- `public/i18n/*/*.json`：`TITLE` 键
- `public/icon.ico` + `public/imgs/logo*.webp`

**勿轻易改 `appId`** —— 会破坏已安装用户的升级识别。

---

## 十三、安全基线

1. **禁用 Node 集成**（在 BrowserWindow 配置中），仅通过 preload 暴露受控 API。
2. **contextIsolation: true** 强制（preload 与 renderer 隔离）。
3. **Token 存储**：`safeStorage`（Electron 原生加密存储），仅通过 `auth.service` 访问。
4. **HTTP 拦截器**：`authInterceptor` 统一注入 Token；`retryInterceptor` 处理 401 静默刷新。
5. **npm 源锁定**：`child/node/.npmrc` 指向私有源，防止安装任意包。
6. **文件关联沙箱**：`.abi` 文件由 `project.service` 校验后才加载，拒绝越权执行。
7. **详细条目**见 [`docs/aily-security-guidelines.md`](./aily-security-guidelines.md)。

---

## 十四、相关文档地图

| 文档 | 用途 |
| --- | --- |
| [`README.md`](../README.md) | 产品快速介绍 |
| [`develop.md`](../develop.md) | 开发环境准备（含 `child/` 资源解压步骤） |
| [`docs/windows-build-deploy.md`](./windows-build-deploy.md) | Windows 打包手册 + 故障排查 |
| [`docs/branding-and-icon-guide.md`](./branding-and-icon-guide.md) | 改名换图指南 |
| [`docs/code-intelligence-guide.md`](./code-intelligence-guide.md) | Monaco + AI 补全接入 |
| [`docs/onboarding.md`](./onboarding.md) | 新手引导系统 API |
| [`docs/aily-security-guidelines.md`](./aily-security-guidelines.md) | 项目安全基线 |
| [`docs/action.service.README.md`](./action.service.README.md) | ActionService（命令分发）参考 |
| [`docs/agent-config-export.md`](./agent-config-export.md) | Agent 配置导出格式 |
| [`CLAUDE.md`](../CLAUDE.md) | Claude Code 协作指南（工程约定速查） |

---

## 十五、一图总结

```
                       青芯驭码 技术全景
                 ┌──────────────────────┐
                 │   最终用户 (桌面端)  │
                 └───────────┬──────────┘
                             │ NSIS 安装包
                             ▼
     ┌───────────────────────────────────────────────┐
     │  Electron 35 外壳 (main + preload + renderer) │
     └───┬───────────────────────────────────────┬───┘
         │                                       │
         ▼                                       ▼
  ┌─────────────┐                     ┌─────────────────┐
  │  渲染进程   │◄── window.electronAPI ──►│  主进程     │
  │  Angular 19 │     (contextBridge)  │  (Node 22)     │
  │  Standalone │                     │                 │
  │             │                     │ · 串口/PTY/npm  │
  │ · Blockly   │                     │ · MCP/probe-rs  │
  │ · Monaco    │                     │ · OAuth/更新器  │
  │ · xterm     │                     │ · 多实例协调    │
  │ · AI 助手   │                     │                 │
  └─────┬───────┘                     └────────┬────────┘
        │                                      │
        │        ┌─────────────────────┐       │
        └───────►│  child/ 外部运行时  │◄──────┘
                 │ Node · 7z · builder │
                 │  · clangd · rg      │
                 └─────────────────────┘
```

---

**文档维护**：本文档与代码同步演进。修改架构时，同步更新本文件；增加新的子系统时，在 §6 扩展，并在 §十二 补充扩展方法。
