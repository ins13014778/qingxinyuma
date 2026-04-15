# 青芯驭码

青芯驭码是一款基于 Electron + Angular 构建的桌面端图形化编程工具，面向嵌入式、硬件原型验证与教学场景，提供项目创建、积木编程、代码编辑、串口调试、AI 助手等能力。

## 项目说明

- 桌面框架：Electron
- 前端框架：Angular 19
- 包管理：npm
- 适用平台：Windows 为主，项目中保留了 macOS / Linux 的打包配置

## 当前仓库包含

- 桌面应用主程序
- Blockly 编辑器与代码编辑器
- 串口工具与项目管理工具
- AI 助手与自定义模型配置能力
- Windows 安装包打包配置

## Windows 快速开始

### 1. 克隆项目

```powershell
git clone <你的仓库地址>
cd qingxinyuma
```

### 2. 安装依赖

```powershell
npm install
cd electron
npm install
cd ..
```

### 3. 启动开发环境

```powershell
npm run electron
```

### 4. 构建 Windows 安装包

```powershell
npm run build
```

构建成功后，安装包默认输出到：

```text
dist\aily-blockly
```

## 文档

- Windows 环境依赖安装与打包部署教程：[`docs/windows-build-deploy.md`](./docs/windows-build-deploy.md)
- 开发说明：[`develop.md`](./develop.md)

## 目录说明

- `src/`：Angular 前端源码
- `electron/`：Electron 主进程与预加载脚本
- `build/`：安装器相关脚本
- `child/`：运行时依赖与外部工具资源
- `public/`：静态资源
- `docs/`：项目文档

## 许可证

本项目遵循 GPL 协议。若你要对外分发、二次开发或商用，请先确认项目中的相关许可证与附加说明是否满足你的使用场景。
