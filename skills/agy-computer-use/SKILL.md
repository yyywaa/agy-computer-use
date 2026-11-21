---
name: agy-computer-use
description: Operate macOS desktop apps visibly via the agy-computer-use MCP server (silent background CGWindowID screenshots, Apple Vision OCR text reading, Swarm-safe serialized GUI clicks/hotkeys, and high-level ChatGPT.app project/agent orchestration with bidirectional callback prompts).
---

# agy-computer-use

Use the `agy-computer-use` MCP tools when you need to delegate work to desktop `ChatGPT.app` (as a visible sub-agent) or interact with any macOS desktop application without disrupting the user.

## Bidirectional Callback Convention (Why It Works)

When delegating a task to `ChatGPT.app` via `chatgpt_new_project_task` or `chatgpt_contact_agent`:

1. **Always include a return-path instruction in your prompt** so ChatGPT knows how to send its result back to the originating Antigravity session (and/or write the full output to an agreed workspace file). For example, append:
   > 完成后请将结论与关键修改摘要发回 Antigravity 对应会话（Conversation ID: `<conversation-id>`），若涉及长文档或代码评审请同步写入项目约定路径。
2. **Inspect silently when checking progress**:
   - Prefer `chatgpt_list_sidebar`, `gui_screenshot`, and `gui_read_ui_text` with default `focus: false`.
   - Call `chatgpt_contact_agent` without `message` to check an open thread silently in the background (**zero focus stealing, zero mouse movement**).
3. **Swarm safety**:
   - All GUI tools are serialized via `fcntl.flock` and automatically restore the user's cursor position, clipboard, and frontmost application after sending or clicking, so multiple Swarm workers can safely share the bridge.
