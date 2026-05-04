<div align="center">

# 青芯驭码 · aily blockly

**一套桌面软件，覆盖从"第一次拖积木"到"把 AI 模型部署进硬件"的完整链路**

[![License](https://img.shields.io/badge/license-GPL-blue.svg)](./LICENSE)
[![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20macOS%20%7C%20Linux-lightgrey.svg)](#支持平台)
[![Electron](https://img.shields.io/badge/Electron-35.x-47848F.svg?logo=electron&logoColor=white)](https://www.electronjs.org/)
[![Angular](https://img.shields.io/badge/Angular-19-DD0031.svg?logo=angular&logoColor=white)](https://angular.io/)
[![Blockly](https://img.shields.io/badge/Blockly-11.x-4285F4.svg)](https://developers.google.com/blockly)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-3178C6.svg?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![Node](https://img.shields.io/badge/Node-22.x-339933.svg?logo=node.js&logoColor=white)](https://nodejs.org/)
[![OpenAI Agents](https://img.shields.io/badge/OpenAI_Agents_SDK-v0.14-412991.svg?logo=openai&logoColor=white)](https://openai.github.io/openai-agents-python/)

[English](./README.md) · **简体中文** · [📖 技术架构](./docs/architecture.md) · [💡 价值主张](./docs/value-proposition.md) · [🌱 五维白皮书](./docs/project-dimensions.md)

</div>

---

## 📖 项目简介

**青芯驭码（aily blockly）** 是一款基于 **Electron + Angular 19** 构建的**桌面级图形化编程 IDE**，面向嵌入式开发、硬件原型验证与 STEM 教学场景。它把 **积木编程（Blockly）、专业代码编辑（Monaco）、AI 助手、串口调试、固件上传、端侧 AI 模型训练与部署** 全部融合在同一款软件中，做到**中文原生、开箱即用、离线可用、可品牌化再分发**。

> 💡 **我们为谁做这个？**
> - 🎓 从小学到大学的 **编程/硬件课堂**
> - 🛠️ 想要快速验证想法的 **创客与嵌入式工程师**
> - 🏢 需要自有品牌 IDE 的 **教育机构与板卡厂商**
> - 🤖 想把 AI 模型跑到硬件上的 **TinyML / 边缘 AI 学习者**

---

## ✨ 核心亮点

<table>
<tr>
<td width="50%" valign="top">

### 🧩 积木 + 代码 双模同屏
- **Blockly 11** 拖拽编程，新手友好
- **Monaco 0.52**（VSCode 同款）专业代码编辑
- **一键切换**，代码自动从积木生成
- 支持学习阶段的**平滑过渡**

### 🤖 AI 原生四层能力
- **L1 代码补全**：本地符号 + 云端 LLM 双通道
- **L2 对话助手**：aily-chat，支持 Markdown/Mermaid
- **L3 Agent 模式**：MCP 协议，AI 可直接调用本地工具
- **L4 多Agent协作**：OpenAI Agents SDK，5 个专家Agent自动分工协作
- 内置 **62 个工具**覆盖项目管理、文件操作、积木拼图、接线图、终端命令
- 可切换到任何 OpenAI 兼容接口或私有化模型

### 🔧 全链路工具链
编程 → 编译 → 上传 → 监视 → 调试，**一个软件搞定所有**，告别五个工具反复切换

### 🎯 广泛硬件支持
- **Arduino** 家族（Uno / Nano / Mega）
- **ESP32 / ESP8266**（`esptool-js` 无需 Python）
- **STM32**（probe-rs 支持 JTAG/SWD）
- **nRF5 系列**（probe-rs）

</td>
<td width="50%" valign="top">

### 🧠 端侧 AI 训练与部署
- 集成 **SSCMA 生态**
- 图像分类 / 目标检测 一体化向导
- **Web Worker 本地训练**，不阻塞 UI
- **采集 → 训练 → 量化 → 部署**，一条龙完成

### 🇨🇳 中文原生 · 离线可用
- UI、文档、AI 对话、示例全中文优先
- 编译、烧录、本地补全**全部可断网使用**
- 国内 npm 镜像可一键切换
- 适配国内教育合规与网络环境

### 📦 开箱即用安装体验
- **一个 NSIS 安装包** = Node + 编译器 + 工具链
- 装完即用，**零环境配置**
- 新手从安装到点亮第一盏 LED：**~5 分钟**

### 🏷️ 开源 + 可品牌化
- **GPL** 开源，代码可审计
- 文档化品牌化指南 → 教育公司/板卡厂商可 **2~4 周出自有品牌 IDE**
- 完整的 NSIS 自定义安装器、文件关联、URL 协议

</td>
</tr>
</table>

---

## 🚀 快速开始

### 环境要求

- **Windows 10/11** 为主（macOS / Linux 亦可开发）
- **Node.js 22.x** · **npm 10+** · **Git**
- Windows 打包需启用 **开发者模式**

### 一分钟启动

```bash
# 1. 克隆仓库
git clone https://github.com/ins13014778/qingxinyuma.git
cd qingxinyuma

# 2. 两层依赖安装（root + electron）
npm install
cd electron && npm install && cd ..

# 3. 启动开发环境（Angular + Electron 同时起）
npm run electron
```

启动后会自动打开青芯驭码桌面窗口。

### 生成 Windows 安装包

```bash
npm run build
```

成功后在 `dist/aily-blockly/` 看到安装包 `青芯驭码-Setup-x.y.z.exe`。

> 🛠️ 详细打包步骤与常见问题 → [`docs/windows-build-deploy.md`](./docs/windows-build-deploy.md)

---

## 🎯 应用场景

| 场景 | 适用人群 | 典型使用 |
| --- | --- | --- |
| 🎓 **K12 STEM 教育** | 小/初/高中学生、教师 | 积木编程 → Arduino / ESP32 传感器项目 |
| 🏫 **高校嵌入式教学** | 大学生、高职生 | 代码模式 + STM32 / ESP32 课程实训 |
| 🛠️ **创客空间** | 培训机构、创客爱好者 | 全流程工具 + 品牌化 IDE 分发 |
| 🚀 **快速原型** | 创业者、硬件工程师 | 15 分钟从 0 到 Demo |
| 🧠 **TinyML 教学** | 研究生、ML 学习者 | 端侧 AI 训练部署一体化 |
| 🏭 **职业培训** | 职校、技校 | 多板卡支持 + 一套教材多层次覆盖 |
| 🔧 **OEM 定制** | 板卡厂商、教育公司 | Fork + 品牌化 → 自有 IDE |

> 📘 详见 [`docs/value-proposition.md`](./docs/value-proposition.md) 中的 **应用场景矩阵**

---

## 🔧 硬件支持

| MCU 家族 | 代表型号 | 烧录方式 | 备注 |
| --- | --- | --- | --- |
| **Arduino AVR** | Uno, Nano, Mega | avrdude (via aily-builder) | 原生 |
| **ESP32 / ESP8266** | ESP32-S3, ESP32-C3, ESP8266 | `esptool-js`（纯 JS） | **无需 Python** |
| **STM32** | F1 / F4 / H7 系列 | probe-rs + JTAG/SWD | 支持 J-Link / ST-LINK |
| **nRF5** | nRF52 系列 | probe-rs | 蓝牙/BLE 场景 |

新增板卡只需在 `src/app/configs/` 添加配置文件，**扩展零侵入**。

---

## 🤖 AI 能力详解

### 四层 AI 架构

```
┌──────────────────────────────────────────────────┐
│  L1 · 代码补全（Monaco 编辑器内嵌）             │
│     · 本地符号扫描（Arduino SDK / 库 .h/.cpp）  │
│     · 云端 LLM 上下文感知                       │
│     · 30 秒缓存，Tab 键接受                     │
├──────────────────────────────────────────────────┤
│  L2 · AI 对话助手（aily-chat）                  │
│     · Markdown / Mermaid / 代码块高亮           │
│     · tiktoken 前端计数，成本可见               │
│     · 项目上下文自动注入                        │
├──────────────────────────────────────────────────┤
│  L3 · MCP Agent（@modelcontextprotocol/sdk）    │
│     · AI 可调用：读文件 / 编译 / 烧录           │
│     · 多步自主执行                              │
├──────────────────────────────────────────────────┤
│  L4 · OpenAI Agents SDK 多Agent系统             │
│     · 5个专家Agent自动分工协作                  │
│     · 62个内置工具覆盖全链路                    │
│     · 生命周期Hooks + Guardrails安全护栏        │
│     · Streaming + SQLite会话持久化              │
└──────────────────────────────────────────────────┘
```

### L4 多Agent协作系统（OpenAI Agents SDK v0.14）

基于 OpenAI Agents SDK 构建的**多Agent协作架构**，主Agent根据任务类型自动委派给专家Agent：

| 专家Agent | 职责 | 工具数 |
| --- | --- | --- |
| 🏗️ **ProjectSpecialist** | 项目创建、编译、开发板切换、配置管理 | 23 |
| 📁 **FileSpecialist** | 文件读写、目录管理、搜索、代码编辑 | 13 |
| 💻 **TerminalSpecialist** | Shell命令、后台进程、终端输出 | 3 |
| 🧩 **BlocklySpecialist** | 积木搜索、创建、连接、配置、代码结构生成 | 10 |
| 🔍 **ResearchSpecialist** | 工具发现、技能加载、硬件/库搜索 | 6 |
| 🔌 **SchematicAgent** | 接线图生成、验证、引脚映射、组件目录 | 9 |

**SDK 特性集成：**
- ✅ Agent 生命周期 Hooks（agent/tool start/end、handoff 事件）
- ✅ Structured Output（Pydantic 类型约束专家输出）
- ✅ Dynamic Instructions（运行时动态系统提示）
- ✅ Guardrails（输入/输出安全护栏，敏感信息检测）
- ✅ Hosted Tools（WebSearch、FileSearch、CodeInterpreter）
- ✅ ModelSettings（per-agent 模型参数调优）
- ✅ SQLite Session（跨会话记忆持久化）
- ✅ Streaming（实时流式输出 + 工具调用追踪）

### AI 配置

在 `src/app/configs/ai-config.ts` 中可配置：

- **endpoint**：任何 OpenAI 兼容接口（OpenAI / Azure / 私有化 / 自建代理）
- **model / temperature / max_tokens**：可调优参数
- **apiKey**：通过 Electron `safeStorage` 加密存储

> 📘 详见 [`docs/code-intelligence-guide.md`](./docs/code-intelligence-guide.md)

---

## 🛠️ 技术栈

### 核心依赖

| 类别 | 技术 | 版本 |
| --- | --- | --- |
| 桌面框架 | Electron | 35.x |
| 前端框架 | Angular | 19.x |
| 语言 | TypeScript | 5.6 |
| 运行时 | Node.js | 22.x |
| 积木引擎 | Blockly | 11.2 |
| 代码编辑器 | Monaco | 0.52 |
| UI 组件库 | ng-zorro-antd | 19.x（dark 主题默认） |
| 终端 | xterm.js | 5.5 |
| ML 框架 | @orama/orama, SSCMA | 3.x |
| AI SDK | @modelcontextprotocol/sdk | 1.25 |
| AI Agent SDK | openai-agents (Python) | 0.14 |
| 串口 | serialport + @lydell/node-pty | — |
| 国际化 | @ngx-translate/core | 16.x |

### 架构概览

```
┌─────────────────────────────────────────────┐
│            Electron Main (Node 22)           │
│  serial · PTY · npm · MCP · probe-rs · 更新器 │
└──────────────────▲───────────────────────────┘
                   │ IPC
┌──────────────────┴───────────────────────────┐
│         Preload · window.electronAPI         │
│          (contextBridge 安全桥接)            │
└──────────────────▲───────────────────────────┘
                   │ window.electronAPI
┌──────────────────┴───────────────────────────┐
│      Angular Renderer (Standalone)           │
│   Blockly · Monaco · xterm · aily-chat       │
└──────────────────────────────────────────────┘
```

> 🏗️ 完整架构、子系统、扩展指南 → [`docs/architecture.md`](./docs/architecture.md)

---

## 📁 项目结构

```
aily-blockly-main/
├── src/                        # Angular 渲染进程
│   ├── app/
│   │   ├── main-window/        # 主窗口壳
│   │   ├── pages/              # 首页 / 示例广场 / 新建项目
│   │   ├── editors/            # Blockly / Monaco / Graph 编辑器
│   │   ├── windows/            # 独立子窗口（设置 / 模型训练 / 部署等）
│   │   ├── tools/              # AI 助手 / 串口监视器 / 模拟器 / 商店
│   │   ├── components/         # 通用 UI 组件
│   │   ├── services/           # 30+ 全局服务（IPC 桥接 + 业务领域）
│   │   ├── configs/            # 板卡 / 菜单 / AI / 功能开关配置
│   │   ├── interceptors/       # HTTP auth / retry
│   │   ├── workers/            # Web Worker（模型训练）
│   │   ├── utils/              # 纯工具函数
│   │   └── types/              # electron.d.ts 等类型声明
│   ├── main.ts                 # Angular 引导入口
│   └── index.html              # SPA 壳
├── electron/                   # Electron 主进程
│   ├── main.js                 # 应用生命周期 / IPC 路由 / 多实例 OAuth
│   ├── preload.js              # contextBridge → window.electronAPI
│   ├── serial.js               # 串口（节流 SerialPort）
│   ├── terminal.js             # node-pty 流式终端
│   ├── npm.js · cmd.js         # 受控子进程
│   ├── mcp.js                  # Model Context Protocol
│   ├── probe-rs.js             # STM32 / nRF5 烧录
│   ├── upload.js               # 固件上传统一入口
│   ├── updater.js              # 自动更新
│   └── window.js               # 窗口管理
├── child/                      # 随安装包分发的外部运行时
│   ├── windows/                # Node 22 + aily-builder + 7z + ripgrep
│   ├── macos/                  # macOS 对应工具
│   └── scripts/                # 跨平台脚本
├── build/                      # 安装器
│   ├── installer.nsh           # NSIS 脚本
│   └── entitlements.mac.plist  # macOS 权限
├── public/                     # 静态资源
│   ├── icon.ico · icon-512.ico # 系统图标
│   ├── imgs/logo*.webp         # 应用内 Logo
│   └── i18n/{zh_cn,en}/        # 多语言文件
├── docs/                       # 文档中心
│   ├── architecture.md         # 📘 技术架构详解
│   ├── value-proposition.md    # 💡 核心优势与应用价值
│   ├── project-dimensions.md   # 🌱 五维白皮书
│   ├── windows-build-deploy.md # 🛠️ Windows 打包手册
│   ├── branding-and-icon-guide.md  # 🏷️ 品牌化指南
│   ├── code-intelligence-guide.md  # 🤖 AI 补全架构
│   ├── onboarding.md               # 🎓 新手引导系统
│   └── aily-security-guidelines.md # 🔒 安全基线
├── CLAUDE.md                   # 🤝 Claude Code 协作指南
├── README.md                   # ★ 本文
├── develop.md                  # 开发者上手
├── package.json                # 根依赖 + electron-builder
├── angular.json                # Angular 工程配置
└── tsconfig*.json              # TypeScript 配置
```

---

## ⚡ 开发指南

### 常用命令

| 命令 | 作用 |
| --- | --- |
| `npm install` | 安装根依赖 |
| `cd electron && npm install` | 安装 Electron 子目录依赖（**必须**） |
| `npm run electron` | 开发模式（Angular + Electron 并行） |
| `npm start` | 仅启动 Angular 开发服务器（端口 4200） |
| `npm run watch` | Angular 开发模式持续构建 |
| `npm run build` | 生产构建 + 打包 Windows 安装包 |
| `npm run build:mac` | macOS 打包（arm64 + x64） |
| `npm run build:mac:universal` | macOS 通用二进制打包 |
| `npm test` | 运行单元测试（Karma + Jasmine） |
| `npx ng test --include='**/auth.service.spec.ts'` | 运行单个测试文件 |

### 添加新的 IPC 能力

```typescript
// 1. electron/your-module.js
function yourMethod() { /* ... */ }
module.exports = { yourMethod };

// 2. electron/main.js 注册
ipcMain.handle('module:your-method', () => yourMethod());

// 3. electron/preload.js 暴露
yourModule: {
  doSomething: () => ipcRenderer.invoke('module:your-method')
}

// 4. src/app/types/electron.d.ts 补类型
interface ElectronAPI {
  yourModule: { doSomething(): Promise<void>; };
}

// 5. src/app/services/your.service.ts 包装
@Injectable({ providedIn: 'root' })
export class YourService {
  do() { return window.electronAPI.yourModule.doSomething(); }
}
```

> 📘 更多扩展场景（新增子窗口 / 新板卡 / 新 Blockly 插件）→ [`docs/architecture.md`](./docs/architecture.md) §十二

### 常见问题排查

| 问题 | 原因 | 解决 |
| --- | --- | --- |
| `Cannot find module 'electron-win-state'` | 只装了根依赖 | `cd electron && npm install` |
| 打包慢 | 首次下载 Electron 二进制 | 配置 `.npmrc` 使用国内镜像 |
| AI 助手 401 | 使用了旧安装包或旧会话 | 重装 + 新建会话 + 确认模型配置 |
| 安装目录名不对 | 只改了 `productName` | 同时改 `name` 为英文 |
| 启动 tcp:4200 超时 | 端口被占用 | 关闭其他 Angular 项目 |

> 🔧 完整故障排查 → [`docs/windows-build-deploy.md`](./docs/windows-build-deploy.md) §12

---

## 🗺️ 发展路线

```
2024                 2025                 2026+
 │                    │                    │
 ▼                    ▼                    ▼
[稳定期]           [智能期]              [生态期]
 v0.5 ~ 0.9        v0.9 ~ 1.x           v1.x ~ 2.x
  │                   │                    │
  ├─ 多硬件支持       ├─ AI 代码补全       ├─ 应用/模型商店
  ├─ 多语言 i18n     ├─ MCP Agent         ├─ 云空间协作
  ├─ 串口监视器      ├─ 多Agent协作 ✅     ├─ 插件生态
  └─ NSIS 打包       ├─ 端侧 AI 训练      └─ Web 版本探索
                     └─ SSCMA 集成

               ← 当前 v0.9.51
```

> 🌱 战略级发展、创新、社会、教育、团队五维度分析 → [`docs/project-dimensions.md`](./docs/project-dimensions.md)

---

## 📚 文档中心

### 给用户

| 文档 | 说明 |
| --- | --- |
| 📖 [README.md](./README.md) | 项目门面（本文） |
| 🛠️ [develop.md](./develop.md) | 开发环境快速上手（中文） |

### 给开发者

| 文档 | 说明 |
| --- | --- |
| 🏗️ [docs/architecture.md](./docs/architecture.md) | 技术架构详解（含扩展指南） |
| 🤝 [CLAUDE.md](./CLAUDE.md) | Claude Code 协作速查 |
| 🤖 [docs/code-intelligence-guide.md](./docs/code-intelligence-guide.md) | AI 代码补全架构 |
| 🎓 [docs/onboarding.md](./docs/onboarding.md) | 新手引导系统 API |
| 🔒 [docs/aily-security-guidelines.md](./docs/aily-security-guidelines.md) | 安全基线 |
| 📋 [docs/action.service.README.md](./docs/action.service.README.md) | ActionService（命令分发）参考 |

### 给运维与商务

| 文档 | 说明 |
| --- | --- |
| 🛠️ [docs/windows-build-deploy.md](./docs/windows-build-deploy.md) | Windows 打包与部署手册 |
| 🏷️ [docs/branding-and-icon-guide.md](./docs/branding-and-icon-guide.md) | 改名换图与品牌化发布 |

### 给决策者与合作方

| 文档 | 说明 |
| --- | --- |
| 💡 [docs/value-proposition.md](./docs/value-proposition.md) | 核心优势与应用价值（含竞品对比 / ROI） |
| 🌱 [docs/project-dimensions.md](./docs/project-dimensions.md) | 发展/创新/社会/教育/团队五维白皮书 |

---

## 🤝 贡献方式

### 新人入门路径

```
Day 1                Day 3                 Day 7              Day 14
  │                    │                     │                  │
  ▼                    ▼                     ▼                  ▼
读 README           读 architecture.md     跑通 npm run electron   提交第一个 PR
跑通安装包          理解子系统分工         选一个 good-first-       (建议从 docs /
了解产品            熟悉 services/         issue                   小 bug 起步)
```

### 欢迎贡献的方向

| 角色 | 贡献方式 |
| --- | --- |
| 💻 **代码贡献者** | 修 bug / 加功能（PR 到 `main`） |
| 🔌 **板卡贡献者** | 提交新板卡配置（`src/app/configs/`） |
| 📚 **教学贡献者** | 提交示例项目 / 课程包 |
| 🌍 **翻译贡献者** | 补充 `public/i18n/` 多语言 |
| ✍️ **文档贡献者** | 完善 `docs/` 或写教程 |
| 🐛 **体验贡献者** | Issues 报告 bug / 提 feature |

### 提交规范

使用 **Conventional Commits**：

```
feat: 新功能
fix: bug 修复
docs: 文档
refactor: 重构
perf: 性能优化
test: 测试
chore: 构建/工具链
ci: CI/CD
```

---

## 🌟 技术特色一览

- ✅ **标准 Angular Standalone**（无 NgModule，全部 `loadComponent`）
- ✅ **Hash 路由**（兼容 Electron `file://` 加载）
- ✅ **Zone 事件合并**（降低高频输入 CD 压力）
- ✅ **contextBridge 严格隔离**（渲染端无 Node 权限）
- ✅ **Web Worker 本地训练**（不阻塞 UI）
- ✅ **asarUnpack 原生模块**（serialport、node-pty 正确加载）
- ✅ **多实例 + OAuth 共享状态**（跨进程协调）
- ✅ **自定义协议 + 文件关联**（`ailyblockly://` + `.abi`）
- ✅ **自动更新 + 差分包**（electron-updater）
- ✅ **ng-zorro-antd 双主题**（深色默认 + 浅色可切换）
- ✅ **tiktoken 前端计数**（AI 对话成本可见）
- ✅ **Mermaid / Shiki / Marked**（富文本渲染）
- ✅ **OpenAI Agents SDK 多Agent协作**（5专家Agent + 62工具 + 生命周期Hooks）
- ✅ **Guardrails 安全护栏**（输入/输出敏感信息检测）
- ✅ **SQLite 会话持久化**（跨会话记忆 + 断点续传）

---

## 📊 项目状态

- **当前版本**：v0.9.51
- **活跃阶段**：🤖 智能期（AI 原生 + 多Agent协作 + 端侧 AI 部署）
- **适用平台**：Windows ✅（主） · macOS ⚠️（测试中） · Linux ⚠️（配置就绪）
- **开发语言**：TypeScript / JavaScript（渲染 + 主进程）
- **构建产物**：NSIS Installer / DMG / AppImage
- **许可证**：GPL

---

## 📄 许可证

本项目采用 [**GPL**](./LICENSE) 协议开源。

- ✅ 允许个人学习、教学使用
- ✅ 允许企业内部使用
- ✅ 允许二次开发与品牌化再发布（需遵守 GPL 条款）
- ⚠️ 如需闭源商用，请联系作者获取商业授权

---

## 🙏 致谢

本项目站在以下优秀开源项目的肩膀上：

- [**Blockly**](https://developers.google.com/blockly) — Google 的可视化编程引擎
- [**Monaco Editor**](https://microsoft.github.io/monaco-editor/) — VSCode 同款编辑器
- [**Electron**](https://www.electronjs.org/) — 跨平台桌面框架
- [**Angular**](https://angular.dev/) — 企业级前端框架
- [**ng-zorro-antd**](https://ng.ant.design/) — Ant Design Angular 实现
- [**xterm.js**](https://xtermjs.org/) — 浏览器终端
- [**esptool-js**](https://github.com/espressif/esptool-js) — ESP32 纯 JS 烧录
- [**probe-rs**](https://probe.rs/) — Rust 嵌入式调试器
- [**@modelcontextprotocol/sdk**](https://github.com/modelcontextprotocol) — AI Agent 协议
- [**OpenAI Agents SDK**](https://openai.github.io/openai-agents-python/) — 多Agent协作框架
- [**Seeed SSCMA**](https://github.com/Seeed-Studio/SSCMA) — 端侧 AI 工具链

以及所有其他在 `package.json` 中列出的依赖项目的贡献者。

---

## 📮 联系与社区

- **GitHub**：[ins13014778/qingxinyuma](https://github.com/ins13014778/qingxinyuma)
- **Issues**：[提交问题](https://github.com/ins13014778/qingxinyuma/issues)
- **Pull Requests**：[提交贡献](https://github.com/ins13014778/qingxinyuma/pulls)

---

<div align="center">

**代码是冷的，教育是暖的。**

**我们希望青芯驭码可以是两者之间的桥。**

⭐ 如果这个项目对你有帮助，欢迎 Star 支持！

[📖 技术架构](./docs/architecture.md) · [💡 价值主张](./docs/value-proposition.md) · [🌱 五维白皮书](./docs/project-dimensions.md) · [🛠️ 开发上手](./develop.md)

</div>
