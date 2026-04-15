# Windows 环境依赖安装与打包部署教程

本文档用于说明如何在 Windows 上从零开始配置环境、安装依赖、启动开发环境，并打包生成可分发的安装程序。

## 1. 适用场景

适用于以下情况：

- 首次在 Windows 上拉起本项目
- 需要重新安装依赖
- 需要构建 Windows 安装包
- 需要排查打包失败、运行失败、缺模块等常见问题

## 2. 建议环境版本

建议使用以下环境：

- Windows 10 或 Windows 11
- Node.js 22.x
- npm 10.x 或 11.x
- Git 最新稳定版

如果你已经安装了其他 Node 版本，也可以先执行以下命令确认：

```powershell
node -v
npm -v
git --version
```

## 3. 必装软件

### 3.1 安装 Git

下载地址：

- [https://git-scm.com/download/win](https://git-scm.com/download/win)

安装时保持默认选项通常即可。

安装完成后验证：

```powershell
git --version
```

### 3.2 安装 Node.js

下载地址：

- [https://nodejs.org/](https://nodejs.org/)

建议安装 Node.js 22 LTS。

安装完成后验证：

```powershell
node -v
npm -v
```

### 3.3 可选：开启 Windows 开发者模式

如果你要本地打包 Electron 安装包，建议开启 Windows 开发者模式。

操作路径：

- `设置`
- `系统`
- `开发者选项`
- 开启 `开发人员模式`

## 4. 获取源码

```powershell
git clone <你的仓库地址>
cd qingxinyuma
```

如果你已经有源码目录，直接进入项目根目录即可。

## 5. 安装项目依赖

本项目有两层依赖：

- 根目录依赖
- `electron` 子目录依赖

两层都必须安装，否则可能会出现打包后运行时报错。

### 5.1 安装根目录依赖

```powershell
npm install
```

### 5.2 安装 Electron 子目录依赖

```powershell
cd electron
npm install
cd ..
```

## 6. 国内镜像配置建议

如果你在中国大陆网络环境下安装依赖较慢，可以在项目根目录 `.npmrc` 中使用如下配置：

```ini
registry=https://registry.npmmirror.com/
electron_mirror=https://npmmirror.com/mirrors/electron/
electron_builder_binaries_mirror=https://npmmirror.com/mirrors/electron-builder-binaries/
```

如果已经配置过，无需重复修改。

## 7. 开发环境准备

本项目运行时依赖 `child` 目录中的若干资源。请确保项目自带资源完整存在。

通常你需要确认这些目录或文件可用：

- `child/windows`
- `child/scripts`
- `public/icon.ico`
- `electron/app-update.yml`

如果仓库已经完整拉取，通常不需要手工补这些内容。

## 8. 启动开发环境

执行：

```powershell
npm run electron
```

该命令会同时启动：

- Angular 开发服务器
- Electron 桌面主程序

如果启动成功，你会看到桌面应用窗口弹出。

## 9. 构建 Windows 安装包

执行：

```powershell
npm run build
```

该命令会完成两步：

1. 执行 Angular 生产构建
2. 执行 `electron-builder` 生成 Windows 安装包

## 10. 打包产物位置

默认输出目录：

```text
dist\aily-blockly
```

常见产物包括：

- `青芯驭码-Setup-0.9.40.exe`
- `win-unpacked\`
- `latest.yml`
- `builder-debug.yml`

其中：

- `青芯驭码-Setup-0.9.40.exe` 是可分发给用户安装的安装包
- `win-unpacked` 是解包后的可执行目录，适合本地排查

## 11. 安装包发布建议

如果你要公开发布，建议使用以下方式之一：

- GitHub Releases 上传安装包
- 自有文件服务器托管安装包
- 配合 `latest.yml` 做静态更新分发

如果你已经关闭了自动更新功能，那么只保留安装包下载即可。

## 12. 常见问题排查

### 12.1 打包后启动报错：`Cannot find module 'electron-win-state'`

原因通常是：

- 只安装了根目录依赖
- 没有安装 `electron` 子目录依赖

解决方法：

```powershell
cd electron
npm install
cd ..
npm run build
```

### 12.2 AI 助手报 401 Unauthorized

如果 AI 助手仍然请求旧的官方接口，通常是以下原因之一：

- 当前运行的不是最新安装包
- 旧版本仍在运行
- 本地历史会话残留旧错误内容

建议处理顺序：

1. 完全退出旧程序
2. 重新安装最新安装包
3. 新建一个全新的 AI 会话
4. 确认模型配置已保存且已启用

### 12.3 打包速度慢

可能原因：

- 首次下载 Electron 运行时
- 首次下载 `electron-builder` 相关二进制
- 网络访问 npm 源较慢

建议：

- 使用 `.npmrc` 国内镜像
- 首次构建耐心等待

### 12.4 构建有 warning 但成功

如果 `npm run build` 最终退出码为 0，且成功生成安装包，通常说明：

- 当前 warning 不阻塞构建
- 可以先继续验证功能是否正常

本项目常见 warning 包括：

- Sass `@import` 过时提示
- CommonJS / 非 ESM 依赖提示
- bundle size budget 提示

### 12.5 安装目录名字不对

安装目录通常受以下字段影响：

- `package.json` 中的 `name`
- `productName`
- NSIS 的默认安装目录推导

如果你想保留中文显示名，但安装目录使用英文，建议：

- `name` 使用英文，如 `qingxinyuma`
- `productName` 使用中文，如 `青芯驭码`

## 13. 建议的完整操作流程

从零开始时，推荐按下面顺序执行：

```powershell
git clone <你的仓库地址>
cd qingxinyuma
npm install
cd electron
npm install
cd ..
npm run build
```

## 14. 构建成功判定标准

满足以下条件即可认为 Windows 打包成功：

- `npm run build` 退出码为 0
- 生成了 `dist\aily-blockly\青芯驭码-Setup-0.9.40.exe`
- `win-unpacked` 目录存在
- 安装包可以启动并看到主界面

## 15. 发布前检查清单

发布前建议至少检查：

- 软件名称是否正确
- 安装包名称是否正确
- 安装目录英文名是否正确
- 图标是否正确
- AI 助手是否正常
- 首页是否符合当前版本要求
- 更新功能是否符合预期

## 16. 额外说明

如果你后续继续修改：

- 软件名称
- 图标
- 安装包名
- AI 助手模型逻辑

建议每次修改后都重新执行一次：

```powershell
npm run build
```

并用最新安装包重新覆盖安装验证。
