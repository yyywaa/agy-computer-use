# agy-computer-use

为了解决 ChatGPT 不说人话、Gemini 模型后端能力稍弱的问题，我尝试将桌面端 `ChatGPT.app` 作为 Antigravity（Gemini）的子 Agent 来协作。

市面上的桥接插件很多基于老的 `codex cli`，功能不全且可用性很低；恰好 AGY 自带的 computer use 体验也不太好，所以我们自己开发了这个轻量级的 macOS 专用 Computer Use MCP 插件，并基于它完成了一个简单好用的 ChatGPT 连接器。

底层基于 macOS 原生辅助功能权限、CoreGraphics 键鼠事件、按 `CGWindowID` 的后台静默截屏以及 Apple 原生 Vision OCR（零 Python 第三方依赖），可能以后会支持Accessibility API，并在此之上专门包装了在 `ChatGPT.app` 中**指定项目发起新任务**、**跟进/联系已在运行的 Agent** 等高频操作，同时支持交互后自动还原鼠标与原前台窗口、文件锁防 Swarm 多 Agent 并发冲突。

## Why it works

1. **AGY 通过 Computer Use 使唤GPT**：agy中的主 Agent 调用 `chatgpt_new_project_task` / `chatgpt_contact_agent`，把任务和上下文直接发进桌面端 `ChatGPT.app` 的指定项目或运行中会话里，用户可以在屏幕上实时看到它干活。
2. **ChatGPT 主动把结果送回 AGY 对应会话**：在插件的提示词（[skills/agy-computer-use/SKILL.md](./skills/agy-computer-use/SKILL.md)）中约定了提示词规范——AGY 派发任务时，会在提示词里明确要求 ChatGPT 在完成后将结果直接发回 AGY 的对应会话（或写入约定文件再通知回传）；需要临时查岗时，AGY 也可以通过后台静默截屏 + Vision OCR 无感读取它的实时状态，不抢鼠标和窗口焦点。

## 快速开始

### 1. 环境与权限

- **系统**：macOS（Python 3.10+，自带 `swiftc`）
- **权限**：在 **系统设置 → 隐私与安全性** 中，为运行宿主/终端开启 **辅助功能（Accessibility）** 和 **屏幕录制（Screen Recording）** 权限。

### 2. 编译、测试并注册到 AGY

```bash
git clone https://github.com/yyywaa/agy-computer-use.git agy-computer-use
cd agy-computer-use

make build          # 编译原生 Swift 辅助工具 bin/win_info 和 bin/vision_ocr
make test           # 运行 MCP 协议握手与静默窗口检测测试
make install-mcp    # 自动注册到 ~/.gemini/config/mcp_config.json
```

刷新 Antigravity 的 MCP 配置（或重开会话）后，主 Agent 和 Swarm 即可直接以原生 `toolcall` 调用以下工具。

## 暴露的工具（MCP Tools）

### ChatGPT 连接器（高频封装）
`chatgpt_list_sidebar`：向agy列出当前可见的项目和运行中的会话。
`chatgpt_new_project_task`：在指定项目下悬停唤出新建按钮、发起新任务并发送提示词，完成后自动还原鼠标与原前台窗口。
`chatgpt_contact_agent`：定位并联系已在运行的 Agent 会话（若所属项目折叠会自动展开）；不传 `message` 时可用于无感查岗并读回当前界面文字。

### 通用 macOS Computer Use 原语
`gui_window_info` / `gui_screenshot` / `gui_read_ui_text`：按 `CGWindowID` 后台静默查窗口、截屏与 Vision OCR 读正文（默认零抢焦点、零碰鼠标）。
`gui_send_message` / `gui_click` / `gui_scroll` / `gui_hotkey`：剪贴板安全粘贴、窗口相对坐标点击/滚动与快捷键，执行完毕自动还原光标、剪贴板和原前台应用，并带文件互斥锁保障 Swarm 并发安全。

## 项目结构

```text
agy-computer-use/
├── native/                     # 原生 Swift 工具（win_info.swift / vision_ocr.swift）
├── src/agy_computer_use/
│   ├── macos.py                # macOS 系统级内核（CoreGraphics、静默截屏、OCR、互斥锁、焦点还原）
│   ├── adapters/chatgpt.py     # ChatGPT.app 连接器适配器
│   └── server.py               # 零依赖 MCP JSON-RPC 2.0 stdio 服务端
├── skills/agy-computer-use/    # 插件提示词与双向回调约定（SKILL.md）
├── tests/                      # 协议与冒烟测试
├── plugin.json                 # Antigravity Plugin 清单
├── mcp_config.json             # MCP Server 配置
└── Makefile
```

## License

[MIT](./LICENSE)
