# 软件名称与图标修改指南

本文档用于说明当前仓库中，软件名称与图标分别由哪些文件控制、修改时需要注意哪些联动项，以及图标资源建议使用的格式。

## 1. 软件名称分布位置

当前项目的软件名称不是只由一个地方控制，而是分散在打包配置、Electron 运行时、安装器脚本、网页标题和多语言文案中。

### 1.1 打包配置

主配置文件：`package.json`

重点字段如下：

- `name`
  - npm 包名。
  - 通常不建议随意修改，除非你明确要连项目包名一起重命名。
- `productName`
  - Electron 应用名。
  - 通常这是最核心的显示名称之一，建议改成目标软件名。
- `description`
  - 软件描述文字。
- `build.appId`
  - 应用唯一标识。
  - 如果是彻底更换品牌或新产品，建议一起改。
  - 如果只是小范围换名，但还希望保留升级识别关系，则需要谨慎修改。
- `build.protocols[].name`
  - 自定义协议显示名称。
- `build.protocols[].schemes`
  - 自定义协议前缀，例如当前是 `ailyblockly`。
  - 如果你的软件已经依赖该协议，修改前需要确认兼容性。
- `build.win.artifactName`
  - Windows 打包出来的文件名模板。
- `build.win.fileAssociations[].name`
  - 文件关联显示名称。
- `build.win.fileAssociations[].description`
  - 文件关联描述。
- `build.mac.artifactName`
  - macOS 打包文件名模板。
- `build.linux.fileAssociations[].name`
  - Linux 文件关联显示名称。
- `build.linux.fileAssociations[].description`
  - Linux 文件关联描述。
- `build.nsis.artifactName`
  - Windows 安装包名称模板。
- `build.nsis.shortcutName`
  - 开始菜单或快捷方式显示名称。

### 1.2 Electron 运行时应用名

文件：`electron/main.js`

关键点：

- `app.setName("aily blockly");`
  - 这里控制 Electron 运行时应用名。
  - 建议与 `package.json` 中的 `productName` 保持一致。

### 1.3 进程名与安装器中的旧进程清理

文件：

- `electron/window.js`
- `build/installer.nsh`

这两个文件中存在写死的进程名：

- `aily blockly.exe`
- `aily blockly`
- `aily-blockly.exe`
- `Aily Blockly.exe`

如果你改了软件名，特别是 Windows 下最终生成的 exe 名称发生变化，这两个文件也需要同步修改。否则会出现以下问题：

- 安装升级时无法正确结束旧进程
- 重启应用逻辑无法命中正确进程
- 卸载或覆盖安装时可能残留旧实例

### 1.4 网页标题与窗口标题

涉及文件：

- `src/index.html`
- `src/app/editors/blockly-editor/blockly-editor.component.ts`
- `src/app/editors/code-editor/code-editor.component.ts`
- `src/app/pages/playground/playground.component.ts`
- `src/app/services/project.service.ts`

这部分控制：

- 浏览器模式下页面标题
- Electron 窗口标题
- 某些默认项目名称或默认显示名

如果只改打包配置而不改这些位置，界面里仍然会继续显示旧名字。

### 1.5 多语言标题文案

目录：`public/i18n/`

例如：

- `public/i18n/zh_cn/zh_cn.json`
- `public/i18n/en/en.json`

当前存在类似字段：

- `"TITLE": "aily blockly IDE"`

如果要做完整改名，建议至少同步修改你实际会使用到的语言包。
如果你的软件只面向中文用户，最低限度应先修改 `zh_cn`。

## 2. 图标与 Logo 分布位置

图标也分为两类：系统图标和界面 Logo。

### 2.1 系统图标

由 `package.json` 的打包配置引用：

- Windows：`public/icon.ico`
- macOS：`public/icon-512.ico`
- Linux：当前也指向 `public/icon.ico`

这类图标主要影响：

- exe 图标
- 安装包图标
- 开始菜单图标
- 桌面快捷方式图标
- 文件关联图标

此外，`package.json` 的 `extraResources` 中还会把 `public/icon.ico` 复制到安装目录内，供安装脚本创建快捷方式时使用。

### 2.2 界面 Logo

文件：

- `public/imgs/logo.webp`
- `public/imgs/logo-light.webp`

这类资源主要影响应用内部页面、启动页或界面展示区域的品牌 Logo，不等同于系统图标。

如果你发现“程序图标改了，但软件首页 Logo 没变”，通常就是因为这里只换了一部分资源。

## 3. 建议的图标格式

### 3.1 Windows

建议使用 `.ico`。

推荐内容：

- 一个多尺寸 ico 文件
- 至少包含以下尺寸：
  - `16x16`
  - `24x24`
  - `32x32`
  - `48x48`
  - `64x64`
  - `128x128`
  - `256x256`

推荐原因：

- 能适配资源管理器、任务栏、快捷方式、安装器等多种显示场景
- 缩放时不容易糊

### 3.2 macOS

标准推荐使用 `.icns`。

当前仓库配置里写的是 `public/icon-512.ico`，这并不是最标准的 macOS 图标做法。

如果你后续确实要发布 macOS 版本，建议改成：

- 一个 `.icns` 文件
- 并同步修改 `package.json` 中 `build.mac.icon`

### 3.3 Linux

通常更推荐 `.png`，尤其是高分辨率透明背景 PNG。

不过当前仓库配置直接复用了 `.ico`。如果你暂时只关心 Windows 打包，可以先不调整。
如果后续要认真适配 Linux 桌面环境，建议单独补一套 PNG 图标资源。

### 3.4 界面 Logo

当前界面 Logo 使用 `.webp`。

建议：

- 保持透明背景
- 同时准备深色版与浅色版
- 分别替换：
  - `logo.webp`
  - `logo-light.webp`

如果你的新品牌没有深浅两套版本，也至少要检查它在深色背景和浅色背景上是否都清晰可见。

## 4. 最小修改清单

如果你想先快速完成“换名 + 换图标”，最低建议修改以下内容。

### 4.1 软件名最低修改项

1. `package.json`
   - `productName`
   - `build.win.artifactName`
   - `build.mac.artifactName`
   - `build.nsis.artifactName`
   - `build.nsis.shortcutName`
2. `electron/main.js`
   - `app.setName(...)`
3. `electron/window.js`
   - 旧进程名检测与结束逻辑
4. `build/installer.nsh`
   - `taskkill` 中的旧 exe 名
5. `src/index.html`
   - `<title>`
6. `public/i18n/zh_cn/zh_cn.json`
   - `"TITLE"`

### 4.2 图标最低修改项

1. `public/icon.ico`
2. `public/imgs/logo.webp`
3. `public/imgs/logo-light.webp`

## 5. 完整改名建议

如果你希望“从安装包到界面到文件关联都彻底统一”，建议按以下顺序处理：

1. 先确定新软件名
   - 中文名
   - 英文名
   - 是否需要新的协议前缀
   - 是否需要新的 `appId`
2. 替换打包配置中的名称
3. 替换 Electron 运行时名称
4. 替换窗口标题与默认显示名
5. 替换多语言标题文案
6. 替换系统图标
7. 替换界面 Logo
8. 重新执行构建验证

## 6. 修改后建议验证项

修改完成后，建议至少验证以下内容：

### 6.1 构建产物

- 安装包文件名是否符合预期
- `win-unpacked` 目录中的 exe 名称是否符合预期

### 6.2 安装与启动

- 安装界面显示名称是否正确
- 安装完成后的桌面快捷方式名称是否正确
- 快捷方式图标是否正确
- 开始菜单名称是否正确
- 启动后的窗口标题是否正确

### 6.3 升级与覆盖安装

- 安装新版本时，旧进程能否被正常关闭
- 是否还残留旧程序名的进程清理逻辑

### 6.4 界面品牌

- 软件首页或欢迎页 Logo 是否更新
- 深色背景和浅色背景下 Logo 是否清晰

## 7. 注意事项

### 7.1 不建议只改一处名称

这个项目里的名字是分散配置的，只改 `productName` 通常不够。常见结果是：

- 安装包名变了
- 但窗口标题没变
- 或者快捷方式图标正常，界面 Logo 仍然是旧品牌

### 7.2 `appId` 修改要谨慎

如果已经存在已安装版本，修改 `appId` 可能影响：

- 升级识别
- 安装覆盖行为
- 某些系统级关联

所以如果只是小范围品牌调整，而不是全新应用，建议先确认是否真的需要修改。

### 7.3 进程名联动最容易漏

当前仓库中，进程清理逻辑和安装器脚本都写死了旧名称。改名后如果不改这里，后续最常见的问题是：

- 新版本安装时关不掉旧版本
- 程序重启流程异常

## 8. 推荐做法

如果你已经确定了新的软件名和新的图标资源，推荐直接一次性完成以下动作：

1. 统一修改所有显示名称
2. 替换 `public/icon.ico`
3. 替换 `public/imgs/logo.webp`
4. 替换 `public/imgs/logo-light.webp`
5. 重新构建
6. 实测安装包、快捷方式、窗口标题和界面 Logo

这样可以避免只改一半导致的品牌不一致问题。
