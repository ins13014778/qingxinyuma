# Branding No Login Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 将软件名称统一为“AI智能编程”，删除首页指定宣传卡片，并取消前端登录要求但保留底层认证/模型相关代码。

**Architecture:** 通过最小范围修改品牌文案、首页模板、头部工具入口和前端门禁函数来实现。保留 `AuthService`、拦截器和自定义模型 API 相关逻辑，不做服务层重构，只在 UI 层与前端访问控制层解除登录约束。

**Tech Stack:** Angular 19, Electron, TypeScript, ng-zorro-antd

---

### Task 1: 统一品牌名

**Files:**
- Modify: `D:\aily-blockly-main\package.json`
- Modify: `D:\aily-blockly-main\electron\main.js`
- Modify: `D:\aily-blockly-main\src\index.html`
- Modify: `D:\aily-blockly-main\public\i18n\zh_cn\zh_cn.json`

### Task 2: 删除首页指定宣传区块

**Files:**
- Modify: `D:\aily-blockly-main\src\app\pages\guide\guide.component.html`
- Modify: `D:\aily-blockly-main\src\app\pages\guide\guide.component.ts`

### Task 3: 移除登录入口与用户中心入口

**Files:**
- Modify: `D:\aily-blockly-main\src\app\main-window\components\header\header.component.ts`
- Modify: `D:\aily-blockly-main\src\app\configs\tool.config.ts`
- Modify: `D:\aily-blockly-main\src\app\configs\menu.config.ts`

### Task 4: 取消前端登录门禁

**Files:**
- Modify: `D:\aily-blockly-main\src\app\components\float-sider\float-sider.component.ts`
- Modify: `D:\aily-blockly-main\src\app\windows\settings\settings.component.ts`
- Modify: `D:\aily-blockly-main\src\app\app.component.ts`

### Task 5: 构建验证

**Files:**
- No file changes

- [ ] Run `npm run build`
- [ ] Confirm the guide page no longer renders the removed sections
- [ ] Confirm the build succeeds without introducing new blocking errors
