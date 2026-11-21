#!/usr/bin/env python3
"""MCP stdio JSON-RPC 2.0 server for agy-computer-use."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

# Allow running directly as `python3 src/agy_computer_use/server.py` without PYTHONPATH
_SRC_DIR = str(Path(__file__).resolve().parents[1])
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

from agy_computer_use import __version__, macos
from agy_computer_use.adapters.chatgpt import (
    CHATGPT_HANDLERS,
    CHATGPT_TOOLS,
    DEFAULT_APP,
    SIDEBAR_MAX_X,
    paste_into_chat_input,
)

SERVER_NAME = "agy-computer-use"


# ---------------------------------------------------------------------------
# Generic macOS Computer Use tool handlers
# ---------------------------------------------------------------------------
def tool_gui_window_info(args: dict[str, Any]) -> dict[str, Any]:
    app_name = args.get("app_name") or DEFAULT_APP
    focus = bool(args.get("focus", False))
    with macos.gui_lock():
        return macos.get_window_info(app_name, focus=focus)


def tool_gui_screenshot(args: dict[str, Any]) -> dict[str, Any]:
    app_name = args.get("app_name") or DEFAULT_APP
    focus = bool(args.get("focus", False))
    output_path = args.get("output_path")
    with macos.gui_lock():
        out, info = macos.capture_window(app_name, focus=focus, output_path=output_path)
        return {
            "screenshot_path": str(out),
            "silent_capture": not focus,
            "window": info,
            "hint": "Use read_file on screenshot_path to inspect the visual UI state.",
        }


def tool_gui_send_message(args: dict[str, Any]) -> dict[str, Any]:
    text = args.get("text")
    if not isinstance(text, str) or not text:
        raise ValueError("'text' must be a non-empty string")
    app_name = args.get("app_name") or DEFAULT_APP
    submit = bool(args.get("submit", True))
    restore_focus = bool(args.get("restore_focus", True))

    with macos.gui_lock():
        with macos.preserve_user_context(app_name, restore=restore_focus):
            shot, info = macos.capture_window(app_name, focus=True)
            items = macos.vision_ocr(shot, info) if macos.VISION_OCR_BIN.exists() else None
            meta = paste_into_chat_input(info, text, submit=submit, ocr_items=items)
            return {
                "sent": True,
                "chars": len(text),
                "restored_user_context": restore_focus,
                **meta,
                "window": info,
            }


def tool_gui_read_ui_text(args: dict[str, Any]) -> dict[str, Any]:
    app_name = args.get("app_name") or DEFAULT_APP
    max_chars = int(args.get("max_chars", 12000))
    focus = bool(args.get("focus", False))
    region = str(args.get("region", "main")).lower()

    with macos.gui_lock():
        shot, info = macos.capture_window(app_name, focus=focus)
        items = macos.vision_ocr(shot, info)
        if region == "main":
            filtered = [i["text"] for i in items if i["cx"] >= SIDEBAR_MAX_X]
        elif region == "sidebar":
            filtered = [i["text"] for i in items if i["cx"] < SIDEBAR_MAX_X]
        else:
            filtered = [i["text"] for i in items]
        joined = "\n".join(filtered)
        truncated = len(joined) > max_chars
        if truncated:
            joined = joined[-max_chars:]
        return {
            "app": app_name,
            "silent_capture": not focus,
            "region": region,
            "segments": len(filtered),
            "truncated": truncated,
            "screenshot_path": str(shot),
            "text": joined,
        }


def tool_gui_click(args: dict[str, Any]) -> dict[str, Any]:
    app_name = args.get("app_name") or DEFAULT_APP
    x = float(args["x"])
    y = float(args["y"])
    clicks = int(args.get("clicks", 1))
    rel = bool(args.get("relative_to_window", True))
    restore_focus = bool(args.get("restore_focus", True))

    with macos.gui_lock():
        with macos.preserve_user_context(app_name, restore=restore_focus):
            info = macos.get_window_info(app_name, focus=True)
            if rel:
                if not info.get("running") or not info.get("has_window"):
                    raise RuntimeError(f"App '{app_name}' has no visible window: {info}")
                abs_x = float(info["x"]) + x
                abs_y = float(info["y"]) + y
            else:
                abs_x, abs_y = x, y
            macos.cg_click(abs_x, abs_y, clicks=clicks)
            return {
                "clicked": [abs_x, abs_y],
                "clicks": clicks,
                "relative_to_window": rel,
                "restored_user_context": restore_focus,
            }


def tool_gui_scroll(args: dict[str, Any]) -> dict[str, Any]:
    app_name = args.get("app_name") or DEFAULT_APP
    delta_y = int(args["delta_y"])
    x = args.get("x")
    y = args.get("y")
    rel = bool(args.get("relative_to_window", True))
    restore_focus = bool(args.get("restore_focus", True))

    with macos.gui_lock():
        with macos.preserve_user_context(app_name, restore=restore_focus):
            info = macos.get_window_info(app_name, focus=True)
            abs_x: float | None = None
            abs_y: float | None = None
            if info.get("running") and info.get("has_window"):
                if x is None or y is None:
                    abs_x = float(info["x"]) + float(info["width"]) * 0.5
                    abs_y = float(info["y"]) + float(info["height"]) * 0.5
                elif rel:
                    abs_x = float(info["x"]) + float(x)
                    abs_y = float(info["y"]) + float(y)
                else:
                    abs_x, abs_y = float(x), float(y)
            macos.cg_scroll(delta_y, abs_x, abs_y)
            return {"scrolled": delta_y, "at": [abs_x, abs_y], "restored_user_context": restore_focus}


def tool_gui_hotkey(args: dict[str, Any]) -> dict[str, Any]:
    app_name = args.get("app_name") or DEFAULT_APP
    key = str(args["key"])
    modifiers = args.get("modifiers") or []
    restore_focus = bool(args.get("restore_focus", True))

    with macos.gui_lock():
        with macos.preserve_user_context(app_name, restore=restore_focus):
            macos.send_hotkey(app_name, key, modifiers)
            return {"app": app_name, "key": key, "modifiers": modifiers, "restored_user_context": restore_focus}


GENERIC_TOOLS: list[dict[str, Any]] = [
    {
        "name": "gui_window_info",
        "description": "Inspect (and optionally focus) a macOS app window's bounds, CGWindowID, frontmost app, and cursor position.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "default": DEFAULT_APP},
                "focus": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "gui_screenshot",
        "description": "Silently capture a macOS app window by CGWindowID (zero focus stealing by default) for visual inspection via read_file.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "default": DEFAULT_APP},
                "focus": {"type": "boolean", "default": False},
                "output_path": {"type": "string"},
            },
        },
    },
    {
        "name": "gui_send_message",
        "description": "Send a message visibly to the active chat/input area via clipboard-safe paste and Return, then restore cursor & frontmost app.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "text": {"type": "string", "description": "Message text to paste and send."},
                "app_name": {"type": "string", "default": DEFAULT_APP},
                "submit": {"type": "boolean", "default": True},
                "restore_focus": {"type": "boolean", "default": True},
            },
            "required": ["text"],
        },
    },
    {
        "name": "gui_read_ui_text",
        "description": "Silently read visible text from a macOS app window using background CGWindowID capture + native Apple Vision OCR.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "default": DEFAULT_APP},
                "region": {"type": "string", "enum": ["main", "sidebar", "all"], "default": "main"},
                "max_chars": {"type": "integer", "default": 12000},
                "focus": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "gui_click",
        "description": "Click a coordinate inside a macOS app window (relative to window top-left by default) and restore cursor & frontmost app.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "x": {"type": "number"},
                "y": {"type": "number"},
                "app_name": {"type": "string", "default": DEFAULT_APP},
                "clicks": {"type": "integer", "default": 1},
                "relative_to_window": {"type": "boolean", "default": True},
                "restore_focus": {"type": "boolean", "default": True},
            },
            "required": ["x", "y"],
        },
    },
    {
        "name": "gui_scroll",
        "description": "Scroll inside a macOS app window (positive delta_y scrolls up, negative scrolls down).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "delta_y": {"type": "integer", "description": "Lines to scroll (negative=down, positive=up)."},
                "x": {"type": "number"},
                "y": {"type": "number"},
                "app_name": {"type": "string", "default": DEFAULT_APP},
                "relative_to_window": {"type": "boolean", "default": True},
                "restore_focus": {"type": "boolean", "default": True},
            },
            "required": ["delta_y"],
        },
    },
    {
        "name": "gui_hotkey",
        "description": "Send a keyboard shortcut to a macOS app and restore cursor & frontmost app.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "key": {"type": "string"},
                "modifiers": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Any of: command, shift, option, control",
                },
                "app_name": {"type": "string", "default": DEFAULT_APP},
                "restore_focus": {"type": "boolean", "default": True},
            },
            "required": ["key"],
        },
    },
]

TOOLS = CHATGPT_TOOLS + GENERIC_TOOLS
HANDLERS = {
    **CHATGPT_HANDLERS,
    "gui_window_info": tool_gui_window_info,
    "gui_screenshot": tool_gui_screenshot,
    "gui_send_message": tool_gui_send_message,
    "gui_read_ui_text": tool_gui_read_ui_text,
    "gui_click": tool_gui_click,
    "gui_scroll": tool_gui_scroll,
    "gui_hotkey": tool_gui_hotkey,
}


# ---------------------------------------------------------------------------
# Minimal MCP stdio JSON-RPC 2.0 loop
# ---------------------------------------------------------------------------
def _send(msg: dict[str, Any]) -> None:
    sys.stdout.write(json.dumps(msg, ensure_ascii=False) + "\n")
    sys.stdout.flush()


def _handle_request(req: dict[str, Any]) -> None:
    req_id = req.get("id")
    method = req.get("method")
    params = req.get("params") or {}

    if method == "initialize":
        proto = params.get("protocolVersion") or "2024-11-05"
        _send(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "result": {
                    "protocolVersion": proto,
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": SERVER_NAME, "version": __version__},
                },
            }
        )
        return

    if method in ("notifications/initialized", "notifications/cancelled"):
        return

    if method == "ping":
        _send({"jsonrpc": "2.0", "id": req_id, "result": {}})
        return

    if method == "tools/list":
        _send({"jsonrpc": "2.0", "id": req_id, "result": {"tools": TOOLS}})
        return

    if method == "tools/call":
        name = params.get("name")
        arguments = params.get("arguments") or {}
        handler = HANDLERS.get(name)
        if not handler:
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "error": {"code": -32601, "message": f"Unknown tool: {name}"},
                }
            )
            return
        try:
            result = handler(arguments)
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [
                            {"type": "text", "text": json.dumps(result, ensure_ascii=False, indent=2)}
                        ],
                        "isError": False,
                    },
                }
            )
        except Exception as exc:
            _send(
                {
                    "jsonrpc": "2.0",
                    "id": req_id,
                    "result": {
                        "content": [{"type": "text", "text": f"Error: {exc}"}],
                        "isError": True,
                    },
                }
            )
        return

    if req_id is not None:
        _send(
            {
                "jsonrpc": "2.0",
                "id": req_id,
                "error": {"code": -32601, "message": f"Method not found: {method}"},
            }
        )


def main() -> None:
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            req = json.loads(line)
        except json.JSONDecodeError as exc:
            sys.stderr.write(f"[{SERVER_NAME}] invalid JSON: {exc}\n")
            sys.stderr.flush()
            continue
        _handle_request(req)


if __name__ == "__main__":
    main()
