# agy-computer-use

A zero-dependency macOS system-level **Computer Use MCP server & Antigravity plugin** designed for single agents and multi-agent **Swarm** workflows.

## Key Features

- **Zero Python dependencies**: Pure Python 3 stdlib + native macOS `CoreGraphics`, `System Events`, `screencapture`, and two tiny precompiled Swift helpers (`win_info` & `vision_ocr`).
- **Silent background inspection**: Captures target windows by `CGWindowID` (`screencapture -x -o -l <wid>`) and runs Apple Vision OCR (~200 ms) **without stealing focus or moving your mouse**.
- **Non-intrusive interaction**: Interactive actions (click, scroll, paste, send) automatically snapshot and restore your cursor position, frontmost application, and clipboard contents immediately after completion.
- **Swarm-safe concurrency**: File-locked (`fcntl.flock`) GUI serialization ensures concurrent Swarm workers never collide on focus, mouse, or clipboard.
- **Pluggable app adapters**: Ships with a high-level `ChatGPT.app` adapter (`chatgpt_list_sidebar`, `chatgpt_new_project_task`, `chatgpt_contact_agent`) alongside generic system-level primitives (`gui_window_info`, `gui_screenshot`, `gui_read_ui_text`, `gui_send_message`, `gui_click`, `gui_scroll`, `gui_hotkey`).

## Architecture

```text
agy-computer-use/
├── native/                     # Native Swift helpers compiled into bin/
│   ├── win_info.swift          # CGWindowID, window bounds, frontmost app & cursor snapshot
│   └── vision_ocr.swift        # Apple Vision accurate zh-Hans / en-US OCR with logical coords
├── src/agy_computer_use/
│   ├── macos.py                # CoreGraphics HID events, locks, context restore, silent capture
│   ├── adapters/chatgpt.py     # High-level ChatGPT.app project & running-agent workflows
│   └── server.py               # Minimal MCP JSON-RPC 2.0 stdio server
├── skills/agy-computer-use/    # Antigravity skill instructions for agents & Swarm workers
├── tests/                      # Protocol & integration smoke tests
├── plugin.json                 # Antigravity plugin manifest
└── mcp_config.json             # MCP server registration
```

## Quick Start (macOS)

Prerequisites: macOS with Xcode Command Line Tools (`swiftc`) and Python 3.10+. Grant **Accessibility** and **Screen Recording** permissions to your terminal / Antigravity host in *System Settings → Privacy & Security*.

```bash
make build          # Compile native Swift helpers into bin/
make test           # Run MCP protocol & silent inspection tests
make install-mcp    # Register this server in ~/.gemini/config/mcp_config.json
```

## Exposed MCP Tools

### Generic macOS Computer Use
- `gui_window_info`: Query window bounds, `CGWindowID`, frontmost app, and cursor position.
- `gui_screenshot`: Silent background window screenshot via `CGWindowID`.
- `gui_read_ui_text`: Silent background Vision OCR text extraction (`main` / `sidebar` / `all`).
- `gui_send_message`: Clipboard-safe paste & submit into the active window, then restore user context.
- `gui_click` / `gui_scroll` / `gui_hotkey`: Window-relative CoreGraphics mouse/scroll and keyboard shortcuts with automatic focus & cursor restoration.

### ChatGPT.app Adapter
- `chatgpt_list_sidebar`: Silently list visible projects and running agent threads with coordinates.
- `chatgpt_new_project_task`: Hover a named project, click its inline compose icon, paste & submit prompt, and restore user context.
- `chatgpt_contact_agent`: Switch to an existing/running agent thread (auto-expanding its project if collapsed), optionally send a follow-up message, and return visible OCR text + screenshot. Read-only inspection on the currently open thread runs silently without touching focus or mouse.

## License

MIT
