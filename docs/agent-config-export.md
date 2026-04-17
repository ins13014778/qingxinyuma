# Agent ?????????

> ?????2026-04-16T14:20:48.276Z
> ?????`src/app/tools/aily-chat/tools/tools.ts`?`ToolRegistry` ?????`AilyChatConfigService`?`MCP` ???`Codex/Claude` ????

## 1. ??

- ? Agent ??????**37**
- ?? Agent ??????**22**
- ???????TOOLS ????**46**
- ????????????`src/app/tools/aily-chat/components/settings/settings.component.ts`
- ?????????`src/app/tools/aily-chat/tools/tools.ts`
- ??????????`src/app/tools/aily-chat/core/tool-registry.ts`

## 2. Agent ?????????

### 2.1 ??/Agent ????

- ?????`src/app/tools/aily-chat/services/aily-chat-config.service.ts`
- ??????`%APPDATA%/aily-chat-config.json`
- ?????
  - `maxCount`???????
  - `enabledTools / disabledTools`???? Agent ????
  - `agentTools.mainAgent`?? Agent ????
  - `agentTools.schematicAgent`??? Agent ????
  - `useCustomApiKey / apiKeys / models`?AI ????
  - `autoSaveEdits`???????
  - `userDisplayName`?????????

### 2.2 ?? App ??

- ?????`src/app/services/config.service.ts`
- ??????`%APPDATA%/config.json`
- ? Agent ?????
  - `theme`???
  - `region`?????
  - `regions.*.npm_registry`?npm ??
  - `regions.*.api_server`???? API
  - `aiChatMode`?AI ????
  - `agentCli`??? CLI ??????????

### 2.3 MCP ??

- ?? MCP ???`src/app/tools/aily-chat/services/mcp.service.ts`
- ?? MCP ?????`src/app/tools/aily-chat/mcp/mcp.json`
- ??? MCP ?????`%APPDATA%/mcp/mcp.json`
- Electron MCP ????`electron/mcp.js`

### 2.4 ? Agent / ?? Agent ??

- ? Agent ???`src/app/tools/aily-chat/tools/runSubagentTool.ts`
- ????? Agent?`schematicAgent`
- ???? Agent ???`src/app/services/background-agent.service.ts`
- ? Agent ?????`src/app/tools/aily-chat/services/subagent-session.service.ts`

### 2.5 Codex / Claude Code ?????????

- Codex ???`%USERPROFILE%/.codex/config.toml`
- Codex ???`%USERPROFILE%/.codex/auth.json`
- Codex MCP ?????????? `.codex/config.toml` ? `[mcp_servers]` ?
- Claude Code ??????????????????/????????

## 3. ? Agent 37 ?????

| # | ??? | ?? | ???? | ???? |
|---|---|---|---|---|
| 1 | `ask_user` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 向用户提出一个或多个问题并等待回答。当你需要用户做出决策、提供额外信息或确认操作时使用此工具。 工具会暂停对话，在聊天界面显示问题和可选项，等待用户回答后继续。... |
| 2 | `search_available_tools` | ????? | `src/app/tools/aily-chat/tools/tools.ts` | 搜索并加载可用的扩展工具。当你需要使用未在当前工具列表中的工具时，调用此工具按关键词搜索。 成功后工具会被加载，可在后续对话中直接调用。 搜索示例： - sea... |
| 3 | `load_skill` | ??? | `src/app/tools/aily-chat/tools/loadSkillTool.ts` | 激活或卸载领域技能。激活后的技能内容会持久注入到每轮请求中，直到卸载。 使用示例： - load_skill({query: "abs-syntax"}) — ... |
| 4 | `run_subagent` | ???? | `src/app/tools/aily-chat/tools/runSubagentTool.ts` |  |
| 5 | `create_project` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 创建一个新项目，返回项目路径。需要提供使用的开发板（如 "@aily-project/board-arduino_uno", "@aily-project/bo... |
| 6 | `execute_command` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 在 PowerShell 中执行系统 CLI 命令。用于执行系统操作或运行特定命令来完成用户任务中的任何步骤。支持命令链，优先使用相对命令和路径以保持终端一致性... |
| 7 | `start_background_command` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 在后台启动一个长时间运行的命令，不等待完成即返回。返回 session_id 用于后续查询输出。 适合场景： - 启动开发服务器（如 npm run dev） ... |
| 8 | `get_terminal_output` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 获取后台命令的当前输出。默认返回自上次读取以来的新输出（增量模式）。 使用场景： - 检查后台命令的执行进度和输出 - 获取服务器启动日志 - 监控编译进度 |
| 9 | `get_context` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 获取当前的环境上下文信息，包括项目路径、当前平台、系统环境等。可以指定获取特定类型的上下文信息。 |
| 10 | `get_project_info` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 获取当前项目信息。如果项目已创建，返回当前项目使用的开发板及已安装的库列表。如果库中包含 readme_ai.md 文档，则同时输出该文件的路径。可用于了解项目... |
| 11 | `read_file` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 读取指定文件的内容。支持完整读取或按行/字节范围读取，自动处理大文件和单行文件。 **读取模式：** 1. **完整读取**（默认）：读取整个文件（文件需小于 ... |
| 12 | `create_file` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 创建新文件并写入内容，需文件完整路径。如果目录不存在会自动创建。可选择是否覆盖已存在的文件。 |
| 13 | `create_folder` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 创建新文件夹。支持递归创建多级目录。 |
| 14 | `edit_file` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 编辑文件工具 - 支持多种编辑模式（推荐使用 String Replace 模式以获得最佳安全性） **编辑模式：** 1. **String Replace*... |
| 15 | `replace_string_in_file` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 精确替换文件中的一段字符串。要求 old_string 在文件中唯一匹配（不允许多个匹配，确保精确修改）。 这是编辑文件最安全的方式： - 自动检测并拒绝多匹配... |
| 16 | `multi_replace_string_in_file` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 批量精确替换 — 在一次调用中对一个或多个文件执行多次字符串替换。每个替换操作按顺序执行。 适合场景： - 需要同时修改多个文件 - 一个文件中需要修改多处不同... |
| 17 | `delete_file` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 删除指定文件。可选择是否在删除前创建备份。 |
| 18 | `delete_folder` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 删除指定文件夹及其内容。可选择是否在删除前创建备份。 |
| 19 | `search_boards_libraries` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 智能开发板和库搜索工具，支持文本搜索和结构化筛选。 使用前可使用get_hardware_categories工具获取可用的分类和筛选维度。 **⭐ 推荐调用方... |
| 20 | `get_hardware_categories` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 获取开发板或库的分类信息，用于引导式选型流程。 **⭐ 推荐使用流程：** 1. 先调用此工具获取分类概览（如传感器有哪些类型？开发板有哪些品牌？） 2. 根据... |
| 21 | `get_board_parameters` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 获取当前项目开发板的详细参数配置工具。 从当前打开项目的开发板配置(board.json)中读取详细的硬件配置参数。 **可用参数类型：** 引脚相关： - a... |
| 22 | `grep_tool` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | - Fast content search tool that works with any codebase size - Searches file con... |
| 23 | `glob_tool` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | - Fast file pattern matching tool that works with any codebase size - Supports g... |
| 24 | `fetch` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 获取网页内容和API数据。支持HTTP/HTTPS请求。 - 内容超过限制字符时自动截断，截断时会提示剩余字符数 - 支持分页读取：当内容被截断时，可用 sta... |
| 25 | `clone_repository` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 克隆/下载远程 Git 仓库到本地。通过平台 zip 下载 API 获取整个仓库代码并解压，无需本地安装 git。 支持平台：GitHub、Gitee、GitL... |
| 26 | `web_search` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 搜索网络以获取最新信息。使用 DuckDuckGo 搜索引擎，返回搜索结果列表（标题、摘要、链接）。 适用场景： - 查找最新的技术文档、库版本信息、API 参... |
| 27 | `todo_write_tool` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | Manage a structured todo list to track progress and plan tasks. Task states: not... |
| 28 | `analyze_library_blocks` | Blockly? | `src/app/tools/aily-chat/tools/registered/blockly-tools.ts` | 分析指定库的块定义，生成 ABS (Aily Block Syntax) 格式的块定义文档。优先使用read_file工具读取库readme，当库对应的 rea... |
| 29 | `get_current_schematic` | ???? | `src/app/tools/aily-chat/tools/registered/schematic-tools.ts` | 读取当前项目已保存的连线图完整内容。 **用于编辑流程：** 用户想修改/添加/删除连线时，先调用本工具获取当前状态，然后编写新的 AWS 内容，调用 vali... |
| 30 | `build_project` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 编译当前项目，检测代码是否能正常编译通过。用于代码编写完成后验证语法和链接是否正确。编译耗时较长（可能数十秒到数分钟），请仅在需要验证时调用。 如果编译出现异常... |
| 31 | `reload_project` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 重新加载当前项目。在修改了库相关的JS文件（如块定义、生成器等）后调用，使修改生效。会先保存项目再重新加载。 |
| 32 | `switch_board` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 在当前项目中切换开发板。需要提供新的开发板包名称（如 "@aily-project/board-esp32_devkitc"）。 切换过程会自动卸载当前开发板包... |
| 33 | `get_board_config` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 获取当前开发板的编译/烧录配置选项及其当前值。 返回信息包括： - 当前开发板名称和类型 - 所有可配置项及其可选值（如上传速度、Flash模式、Flash大小... |
| 34 | `set_board_config` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 修改当前开发板的编译/烧录配置项。需先通过 get_board_config 工具获取可用的配置项和可选值。 使用方式： 1. 先调用 get_board_co... |
| 35 | `memory` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 持久化记忆工具 — 跨会话保存和读取笔记、偏好、项目约定等信息。 两层作用域： - **project**: 项目记忆，存储在项目根目录的 aily.md 中。... |
| 36 | `get_errors` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 获取当前项目或指定文件的错误诊断信息。整合 lint 错误和编译错误，一次性返回所有已知问题。 数据来源： 1. **Lint 错误**: JSON/JS 文件... |
| 37 | `save_arch` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 保存/覆盖框架图到项目目录下的 arch.md 文件。当你生成了 mermaid 框架图后，调用此工具将其持久化保存，无需用户手动点击保存按钮。 传入 merm... |

## 4. ?? Agent 22 ?????

| # | ??? | ?? | ???? | ???? |
|---|---|---|---|---|
| 1 | `ask_user` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 向用户提出一个或多个问题并等待回答。当你需要用户做出决策、提供额外信息或确认操作时使用此工具。 工具会暂停对话，在聊天界面显示问题和可选项，等待用户回答后继续。... |
| 2 | `search_available_tools` | ????? | `src/app/tools/aily-chat/tools/tools.ts` | 搜索并加载可用的扩展工具。当你需要使用未在当前工具列表中的工具时，调用此工具按关键词搜索。 成功后工具会被加载，可在后续对话中直接调用。 搜索示例： - sea... |
| 3 | `get_context` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 获取当前的环境上下文信息，包括项目路径、当前平台、系统环境等。可以指定获取特定类型的上下文信息。 |
| 4 | `get_project_info` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 获取当前项目信息。如果项目已创建，返回当前项目使用的开发板及已安装的库列表。如果库中包含 readme_ai.md 文档，则同时输出该文件的路径。可用于了解项目... |
| 5 | `read_file` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 读取指定文件的内容。支持完整读取或按行/字节范围读取，自动处理大文件和单行文件。 **读取模式：** 1. **完整读取**（默认）：读取整个文件（文件需小于 ... |
| 6 | `edit_file` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 编辑文件工具 - 支持多种编辑模式（推荐使用 String Replace 模式以获得最佳安全性） **编辑模式：** 1. **String Replace*... |
| 7 | `replace_string_in_file` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 精确替换文件中的一段字符串。要求 old_string 在文件中唯一匹配（不允许多个匹配，确保精确修改）。 这是编辑文件最安全的方式： - 自动检测并拒绝多匹配... |
| 8 | `multi_replace_string_in_file` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 批量精确替换 — 在一次调用中对一个或多个文件执行多次字符串替换。每个替换操作按顺序执行。 适合场景： - 需要同时修改多个文件 - 一个文件中需要修改多处不同... |
| 9 | `delete_file` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 删除指定文件。可选择是否在删除前创建备份。 |
| 10 | `delete_folder` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | 删除指定文件夹及其内容。可选择是否在删除前创建备份。 |
| 11 | `get_board_parameters` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 获取当前项目开发板的详细参数配置工具。 从当前打开项目的开发板配置(board.json)中读取详细的硬件配置参数。 **可用参数类型：** 引脚相关： - a... |
| 12 | `grep_tool` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | - Fast content search tool that works with any codebase size - Searches file con... |
| 13 | `glob_tool` | ??? | `src/app/tools/aily-chat/tools/registered/file-tools.ts` | - Fast file pattern matching tool that works with any codebase size - Supports g... |
| 14 | `fetch` | ??/??? | `src/app/tools/aily-chat/tools/registered/project-tools.ts` | 获取网页内容和API数据。支持HTTP/HTTPS请求。 - 内容超过限制字符时自动截断，截断时会提示剩余字符数 - 支持分页读取：当内容被截断时，可用 sta... |
| 15 | `generate_schematic` | ???? | `src/app/tools/aily-chat/tools/registered/schematic-tools.ts` | 生成硬件接线图的核心工具。分析开发板与外设的引脚映射，返回引脚摘要和生成规则。你需要根据返回内容编写 AWS (Aily Wiring Syntax) 连线，再... |
| 16 | `get_pinmap_summary` | ???? | `src/app/tools/aily-chat/tools/registered/schematic-tools.ts` | **已废弃** — generate_schematic 内部已包含完整引脚摘要，通常无需单独调用此工具。 |
| 17 | `get_component_catalog` | ???? | `src/app/tools/aily-chat/tools/registered/schematic-tools.ts` | 获取当前项目的组件目录：开发板 + 已安装的传感器/外设库 + 软件库，列出所有可用型号和 pinmapId。 **⭐ 连线流程第一步：** 在生成接线图前，先... |
| 18 | `get_project_context` | ???? | `src/app/tools/aily-chat/tools/registered/schematic-tools.ts` | 一次获取项目上下文 + 组件目录，合并了 get_context 和 get_component_catalog 的功能。 **⭐ 连线流程第一步：** 替代原... |
| 19 | `validate_schematic` | ???? | `src/app/tools/aily-chat/tools/registered/schematic-tools.ts` | 验证 AWS 接线图并保存。这是连线工作流的**最终步骤**，集验证 + 保存 + 刷新为一体。 **功能：** - 解析 AWS 语法，检查引脚、冲突、电压等... |
| 20 | `get_current_schematic` | ???? | `src/app/tools/aily-chat/tools/registered/schematic-tools.ts` | 读取当前项目已保存的连线图完整内容。 **用于编辑流程：** 用户想修改/添加/删除连线时，先调用本工具获取当前状态，然后编写新的 AWS 内容，调用 vali... |
| 21 | `generate_pinmap` | ???? | `src/app/tools/aily-chat/tools/registered/schematic-tools.ts` | 为缺少引脚配置的组件（开发板、传感器、模块等任意类型）准备生成素材。返回 README、示例代码和 pinmap 模板，供你生成 pinmap JSON，再调用... |
| 22 | `save_pinmap` | ???? | `src/app/tools/aily-chat/tools/registered/schematic-tools.ts` | 保存你生成的 pinmap JSON 到库目录，并自动创建/更新 pinmap_catalog.json，将状态置为 "available"。配合 genera... |

## 5. ????????

### 5.1 ??????????/??????

- `src/app/tools/aily-chat/tools/tools.ts`
  - ?? TOOLS ??
  - ?? agents ??
  - ?? description / input_schema
  - ????? 37 / 22 ????????????

### 5.2 ???????????

- ??/?????`src/app/tools/aily-chat/tools/registered/project-tools.ts`
- ?????`src/app/tools/aily-chat/tools/registered/file-tools.ts`
- Blockly ???`src/app/tools/aily-chat/tools/registered/blockly-tools.ts`
- ??????`src/app/tools/aily-chat/tools/registered/schematic-tools.ts`
- ABS/ABI ???`src/app/tools/aily-chat/tools/registered/abs-tools.ts`
- ???????`src/app/tools/aily-chat/tools/registered/register-all.ts`
- ???????`src/app/tools/aily-chat/core/tool-registry.ts`

### 5.3 ??????????? ToolRegistry ?????????

???
- ??????? `TOOLS` ???? agents
- ToolRegistry ????????????/????
- ???????????? `tools.ts` ??

## 6. ? Agent ????????

### 6.1 ? Agent
- UI ???`src/app/tools/aily-chat/aily-chat.component.ts`
- ?????`src/app/tools/aily-chat/services/chat-engine.service.ts`
- ask_user / tool approval / todo / model switch ??????

### 6.2 ?? Agent
- ????`schematicAgent`
- ???????`src/app/services/background-agent.service.ts`
- ??? Agent ???`src/app/tools/aily-chat/services/subagent-session.service.ts`
- ??????? schematic-tools.ts

### 6.3 MCP
- ???????? MCP client ???????????????
- ???? Codex ???? 37/22 ?????????? **MCP Bridge**?? ToolRegistry ???? MCP tools

## 7. ???? MCP ????

???? `src/app/tools/aily-chat/mcp/mcp.json` ????

```json
{
  "mcpServers": {
  }
}
```

## 8. ??????

???????????? `tools.ts` ?? `TOOLS` ??????

- ??? JSON?`docs/agent-tool-export.json`
- ?????`docs/agent-config-export.md`

???????????????????????
- ? `TOOLS` ???? agents
- ?????????????
- ??????? Agent ??????
- ? MCP ?????? server ??

## 9. ????

- `docs/agent-tool-export.json`
- `docs/agent-config-export.md`
