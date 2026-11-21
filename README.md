# agy-computer-use

> 让你的 Agent（以及多 Agent Swarm）在不打扰你工作的前提下，以可视化、低侵入的方式操控 macOS 桌面应用。
>
> A zero-dependency macOS system-level **Computer Use MCP server & Antigravity plugin** built for single agents and concurrent **Swarm** workflows.

---

## 为什么做这个项目（Why We Built This）

在日常开发与科研工作流里，AI Agent（例如 Antigravity 及其 Swarm）已经很擅长读写文件和执行命令行，但一旦需要和**桌面应用**协同工作——尤其是像 macOS 版 `ChatGPT.app` 这样把项目上下文、多模态能力与可视化推理过程都放在 GUI 里的应用——传统方案往往会遇到四个非常真实的痛点：

1. **纯 CLI 黑箱、功能不全**：后台命令行往往看不到实时思考与交互界面，也缺少桌面端独有的项目管理与完整能力；
2. **传统无障碍树在 Electron 应用上失灵**：许多现代桌面应用（包括新版 `ChatGPT.app`）内部使用 Electron / WebView 渲染并关闭了外部 `AXManualAccessibility`，导致常规 Accessibility 自动化只能读到空壳；
3. **粗暴抢鼠标、抢焦点、毁剪贴板**：普通的 GUI 脚本一运行就霸占屏幕和光标，用户根本没法同时干活；
4. **多 Agent（Swarm）并发必撞车**：多个 worker 同时发消息或点击窗口时，焦点和剪贴板会瞬间乱套。

**`agy-computer-use` 就是为了解决这四个问题而写的**：

- **后台静默“看”屏幕**：通过原生 `CGWindowID` 按窗口 ID 静默截屏（`screencapture -x -o -l`）并结合 Apple 原生 `Vision` OCR（约 200 ms 完成中英文精准识别与像素定位），只要是只读查看进度或读回复，**零抢焦点、零切窗口、零碰鼠标**；
- **交互完瞬间归位**：只有真正需要点击、滚动或发送消息时才短暂借用焦点，并在执行前自动快照你的鼠标坐标、当前前台应用与剪贴板内容，动作完成立刻原地还原；
- **Swarm 并发安全**：所有 GUI 操作经过文件互斥锁（`fcntl.flock`）严格串行化，多个 Swarm worker 可以放心地把它当标准 `toolcall` 并发调用；
- **零 Python 第三方依赖**：纯 Python 3 标准库 + CoreGraphics + 两个不到百行的原生 Swift 辅助程序，不折腾虚拟环境，不挑系统包版本；
- **通用内核 ＋ 可插拔应用适配器**：底层暴露 7 个适用于任意 macOS 应用的系统级原语，上层内置 `ChatGPT.app` 适配器作为标杆示例（将“在指定项目开新任务”和“联系已在运行的 agent”封装成一步到位的语义化 toolcall）。

---

## 快速开始（How to Use）

### 1. 环境准备

- **系统**：macOS（Apple Silicon / Intel 均可）
- **工具**：Python 3.10+、Xcode Command Line Tools（系统自带 `swiftc`）
- **系统权限**：在 **系统设置 → 隐私与安全性** 中，为你的终端或 Antigravity 宿主开启以下两项原生权限：
  - **辅助功能（Accessibility）**：用于发送鼠标、滚轮与键盘快捷键事件；
  - **屏幕录制（Screen Recording）**：用于按 `CGWindowID` 静默截取目标应用窗口。

### 2. 编译、测试与一键注册 MCP

```bash
git clone <your-repo-url> agy-computer-use
cd agy-computer-use

make build          # 将 native/*.swift 编译为原生二进制 bin/win_info 和 bin/vision_ocr
make test           # 运行 MCP 协议握手与无侵入静默窗口检测测试
make install-mcp    # 自动注册到 ~/.gemini/config/mcp_config.json
```

注册完成后，在 Antigravity 中刷新 MCP 配置（或重启会话），主 Agent 与 Swarm 中的 Worker 即可直接以原生 `toolcall` 形式调用全部工具。

---

## 典型使用方式

### 场景 A：让 Agent 静默查看桌面应用状态（不打扰你干活）

当 `ChatGPT.app` 或其他应用在后台运行时，调用只读工具不会切换你的当前窗口，也不会移动鼠标：

- 调用 `chatgpt_list_sidebar()`：后台静默扫描侧边栏，返回所有可见项目名、运行中的会话名称及相对坐标。
- 调用 `gui_screenshot(app_name="ChatGPT")`：按 `CGWindowID` 后台截屏，返回图片路径供 Agent 用 `read_file` 查看画面。
- 调用 `gui_read_ui_text(app_name="ChatGPT", region="main")`：后台静默截图并用 Apple Vision OCR 提取主区域纯文本。

### 场景 B：在指定项目里开一个新任务

当主 Agent 或某个 Swarm Worker 需要把一项评审、调研或子任务交给 `ChatGPT.app` 里特定项目的 Agent 时：

```json
{
  "tool": "chatgpt_new_project_task",
  "arguments": {
    "project_name": "data-driven-rust-protection",
    "prompt": "请严格评审 docs/architecture-plan.md 中的电化学可辨识性与统计边界。"
  }
}
```

插件会自动在侧边栏定位该项目 → 悬停唤出行尾新建按钮 → 点击打开新任务 → 定位底部输入框并剪贴板安全粘贴发送 → 立即将鼠标指针、剪贴板和前台应用还原回你原本的界面，同时返回发送后的截图路径供确认。

### 场景 C：联系已经在运行的 Agent（或静默查岗）

```json
{
  "tool": "chatgpt_contact_agent",
  "arguments": {
    "agent_query": "代码架构预备计划",
    "project_name": "data-driven-rust-protection",
    "message": "请重点补充全频段 EIS 拆解的拟合诊断验收条件。"
  }
}
```

- 如果所属项目当前处于折叠状态，传入 `project_name` 会自动先展开再定位目标会话；
- 如果只想**查看这个 Agent 写完没有**，省略 `message` 字段即可；若 `ChatGPT.app` 当前正好停留在该会话，查岗过程将全程在后台静默完成，完全不碰鼠标与窗口焦点。

### 场景 D：操控任意其他 macOS 应用

底层 7 个通用工具均接受 `app_name` 参数（例如 `"Safari"`、`"Finder"`、`"Terminal"` 等），坐标默认采用**相对目标窗口左上角的逻辑像素**，窗口挪动也不受影响：

| 工具名 | 分类 | 说明 | 默认静默 / 自动还原 |
|---|---|---|---|
| `gui_window_info` | 通用底层 | 获取窗口坐标、`CGWindowID`、当前前台应用与鼠标位置 | 静默 |
| `gui_screenshot` | 通用底层 | 按 `CGWindowID` 截取单窗口画面 | 静默（`focus: false`） |
| `gui_read_ui_text` | 通用底层 | 静默截屏 ＋ Apple Vision OCR 提取文字（`main`/`sidebar`/`all`） | 静默 |
| `gui_send_message` | 通用底层 | 剪贴板安全粘贴并回车发送 | 自动还原焦点/鼠标/剪贴板 |
| `gui_click` | 通用底层 | 基于 CoreGraphics 的窗口相对/绝对坐标点击 | 自动还原焦点/鼠标 |
| `gui_scroll` | 通用底层 | 基于 CoreGraphics 的窗口滚轮滚动 | 自动还原焦点/鼠标 |
| `gui_hotkey` | 通用底层 | 发送组合快捷键（如 `Cmd+N`、`Esc`、`Return`） | 自动还原焦点/鼠标 |
| `chatgpt_list_sidebar` | ChatGPT 适配器 | 列出侧边栏可见项目与运行中的会话 | 静默 |
| `chatgpt_new_project_task` | ChatGPT 适配器 | 在指定项目下新建任务并发送指令 | 自动还原焦点/鼠标/剪贴板 |
| `chatgpt_contact_agent` | ChatGPT 适配器 | 切入已有会话（可自动展开项目）、追加消息或静默读回复 | 查岗静默 / 发消息自动还原 |

---

## 项目结构与扩展新适配器

```text
agy-computer-use/
├── native/                     # 原生 Swift 源码（make build 编译至 bin/）
│   ├── win_info.swift          # 获取 CGWindowID、窗口边界、前台应用与鼠标位置
│   └── vision_ocr.swift        # 调用 Apple Vision 进行高精度中英文 OCR 与坐标映射
├── src/agy_computer_use/
│   ├── macos.py                # 通用系统内核：CoreGraphics 事件、静默截屏、互斥锁、焦点还原
│   ├── adapters/chatgpt.py     # ChatGPT.app 适配器（新增其他 App 适配器可参照此文件）
│   └── server.py               # 零依赖 MCP JSON-RPC 2.0 stdio 服务端
├── skills/agy-computer-use/    # Antigravity 技能说明文档（SKILL.md）
├── tests/                      # 端到端 MCP 协议与静默窗口检测测试
├── plugin.json                 # Antigravity Plugin 清单
├── mcp_config.json             # 插件 MCP 配置
└── Makefile                    # 构建、测试与本地注册入口
```

如需接入其他桌面应用，只需在 `src/agy_computer_use/adapters/` 下新增模块，复用 `macos.py` 提供的 `gui_lock`、`preserve_user_context`、`capture_window`、`vision_ocr` 与 `paste_text_safe`，再将工具定义与处理函数注册到 `server.py` 即可。

---

## License

[MIT](./LICENSE)
