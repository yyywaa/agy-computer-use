---
name: agy-computer-use
description: Operate macOS desktop apps visibly via the agy-computer-use MCP server (silent background CGWindowID screenshots, Apple Vision OCR text reading, Swarm-safe serialized GUI clicks/hotkeys, and high-level ChatGPT.app project/agent orchestration).
---

# agy-computer-use

Use the `agy-computer-use` MCP tools when you need to inspect or interact with a live macOS desktop application (especially `ChatGPT.app`) without blocking the user's workflow.

## Recommended Patterns

1. **Silent read-only inspection first**:
   - Prefer `chatgpt_list_sidebar`, `gui_screenshot`, and `gui_read_ui_text` with default `focus: false`.
   - These capture the target window by `CGWindowID` in the background with **zero focus stealing and zero mouse movement**.
2. **Start a new task in a specific ChatGPT.app project**:
   - Call `chatgpt_new_project_task(project_name="<project>", prompt="<instruction>")`.
   - The tool hovers the project row, clicks the inline compose button, pastes safely via clipboard (restoring previous clipboard contents), submits, and immediately restores the user's cursor & frontmost app.
3. **Contact or check on an existing/running agent**:
   - Call `chatgpt_contact_agent(agent_query="<thread name>", project_name="<optional parent project>", message="<optional follow-up>")`.
   - Omit `message` to inspect current progress; if `ChatGPT.app` is already displaying that thread, inspection runs completely silently in the background.
4. **Swarm safety**:
   - All GUI tools are file-locked (`fcntl.flock`), so multiple Swarm workers can safely invoke them without colliding on focus, cursor, or clipboard.
