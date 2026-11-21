"""High-level semantic adapter for macOS ChatGPT.app (Projects & running agent threads)."""

from __future__ import annotations

import time
from typing import Any

from agy_computer_use import macos

DEFAULT_APP = "ChatGPT"
SIDEBAR_MAX_X = 290.0
PROJECT_NEW_BTN_X = 258.0


def _normalize_query(s: str) -> str:
    return "".join(s.lower().split())


def _find_sidebar_item(
    items: list[dict[str, Any]], query: str, min_y: float = 0.0
) -> dict[str, Any] | None:
    q = _normalize_query(query)
    if not q:
        return None
    sidebar = [i for i in items if i["cx"] < SIDEBAR_MAX_X and i["cy"] >= min_y]
    matches = [i for i in sidebar if q in _normalize_query(i["text"])]
    if matches:
        matches.sort(key=lambda i: (len(i["text"]), i["cy"]))
        return matches[0]
    if len(q) >= 6:
        prefix = q[: max(6, len(q) // 2)]
        partial = [i for i in sidebar if prefix in _normalize_query(i["text"])]
        if partial:
            partial.sort(key=lambda i: (len(i["text"]), i["cy"]))
            return partial[0]
    return None


def paste_into_chat_input(
    info: dict[str, Any],
    text: str,
    submit: bool = True,
    ocr_items: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    input_pt: tuple[float, float] | None = None
    if ocr_items:
        placeholders = ("发送消息", "询问", "message", "ask anything", "输入消息", "向")
        candidates = [
            i
            for i in ocr_items
            if i["cx"] > SIDEBAR_MAX_X
            and i["cy"] > float(info["height"]) * 0.55
            and any(p in i["text"].lower() for p in placeholders)
        ]
        if candidates:
            candidates.sort(key=lambda i: i["cy"], reverse=True)
            best = candidates[0]
            input_pt = (float(info["x"]) + best["cx"], float(info["y"]) + best["cy"])

    if input_pt is None:
        main_center_x = float(info["x"]) + SIDEBAR_MAX_X + (float(info["width"]) - SIDEBAR_MAX_X) * 0.45
        main_bottom_y = float(info["y"]) + float(info["height"]) - 42.0
        input_pt = (main_center_x, main_bottom_y)

    macos.cg_click(input_pt[0], input_pt[1], clicks=1)
    time.sleep(0.15)
    macos.paste_text_safe(text, submit=submit)
    return {"input_clicked_abs": [round(input_pt[0], 1), round(input_pt[1], 1)], "submitted": submit}


def tool_chatgpt_list_sidebar(args: dict[str, Any]) -> dict[str, Any]:
    app_name = args.get("app_name") or DEFAULT_APP
    focus = bool(args.get("focus", False))
    with macos.gui_lock():
        shot, info = macos.capture_window(app_name, focus=focus)
        items = macos.vision_ocr(shot, info)
        sidebar = [
            {"text": i["text"], "cx": i["cx"], "cy": i["cy"]}
            for i in items
            if i["cx"] < SIDEBAR_MAX_X and i["cy"] > 50.0
        ]
        return {
            "app": app_name,
            "silent_capture": not focus,
            "window": info,
            "screenshot_path": str(shot),
            "sidebar_items": sidebar,
        }


def tool_chatgpt_new_project_task(args: dict[str, Any]) -> dict[str, Any]:
    project_name = args.get("project_name")
    prompt = args.get("prompt")
    if not isinstance(project_name, str) or not project_name.strip():
        raise ValueError("'project_name' must be a non-empty string")
    if not isinstance(prompt, str) or not prompt.strip():
        raise ValueError("'prompt' must be a non-empty string")

    app_name = args.get("app_name") or DEFAULT_APP
    submit = bool(args.get("submit", True))
    restore_focus = bool(args.get("restore_focus", True))

    with macos.gui_lock():
        with macos.preserve_user_context(app_name, restore=restore_focus):
            shot0, info = macos.capture_window(app_name, focus=True)
            items0 = macos.vision_ocr(shot0, info)
            proj = _find_sidebar_item(items0, project_name)

            if proj is None:
                sb_x = float(info["x"]) + 150.0
                sb_y = float(info["y"]) + float(info["height"]) * 0.55
                macos.cg_scroll(-10, sb_x, sb_y)
                time.sleep(0.30)
                shot0, info = macos.capture_window(app_name, focus=True)
                items0 = macos.vision_ocr(shot0, info)
                proj = _find_sidebar_item(items0, project_name)

            if proj is None:
                sidebar_texts = [i["text"] for i in items0 if i["cx"] < SIDEBAR_MAX_X]
                raise RuntimeError(
                    f"Project '{project_name}' not found in visible sidebar. Visible items: {sidebar_texts}"
                )

            abs_proj_x = float(info["x"]) + float(proj["cx"])
            abs_proj_y = float(info["y"]) + float(proj["cy"])
            macos.cg_move(abs_proj_x, abs_proj_y)
            time.sleep(0.30)

            abs_btn_x = float(info["x"]) + PROJECT_NEW_BTN_X
            macos.cg_click(abs_btn_x, abs_proj_y, clicks=1)
            time.sleep(0.45)

            shot_new, info_new = macos.capture_window(app_name, focus=True)
            items_new = macos.vision_ocr(shot_new, info_new)
            send_meta = paste_into_chat_input(info_new, prompt, submit=submit, ocr_items=items_new)

            time.sleep(0.35)
            shot_after, info_after = macos.capture_window(app_name, focus=False)
            return {
                "ok": True,
                "action": "new_project_task",
                "project_matched": proj["text"],
                "project_row_rel": [proj["cx"], proj["cy"]],
                "chars_sent": len(prompt),
                "restored_user_context": restore_focus,
                **send_meta,
                "screenshot_path": str(shot_after),
                "window": info_after,
            }


def tool_chatgpt_contact_agent(args: dict[str, Any]) -> dict[str, Any]:
    agent_query = args.get("agent_query")
    if not isinstance(agent_query, str) or not agent_query.strip():
        raise ValueError("'agent_query' must be a non-empty string")

    project_name = args.get("project_name")
    message = args.get("message")
    submit = bool(args.get("submit", True))
    read_reply = bool(args.get("read_reply", True))
    restore_focus = bool(args.get("restore_focus", True))
    app_name = args.get("app_name") or DEFAULT_APP

    with macos.gui_lock():
        info_now = macos.get_window_info(app_name, focus=False)
        already_on_target = _normalize_query(agent_query) in _normalize_query(info_now.get("title") or "")
        if already_on_target and not (isinstance(message, str) and message.strip()):
            shot_silent, info_silent = macos.capture_window(app_name, focus=False)
            items_silent = macos.vision_ocr(shot_silent, info_silent) if read_reply else []
            main_text = "\n".join(i["text"] for i in items_silent if i["cx"] >= SIDEBAR_MAX_X) if read_reply else ""
            return {
                "ok": True,
                "action": "contact_agent",
                "silent_read_only": True,
                "agent_matched": info_silent.get("title") or agent_query,
                "expanded_project": False,
                "sent": False,
                "screenshot_path": str(shot_silent),
                "visible_main_text": main_text,
                "window": info_silent,
            }

        with macos.preserve_user_context(app_name, restore=restore_focus):
            shot0, info = macos.capture_window(app_name, focus=True)
            items0 = macos.vision_ocr(shot0, info)
            target = _find_sidebar_item(items0, agent_query)

            expanded_project = False
            if target is None and isinstance(project_name, str) and project_name.strip():
                proj = _find_sidebar_item(items0, project_name)
                if proj is not None:
                    macos.cg_click(float(info["x"]) + float(proj["cx"]), float(info["y"]) + float(proj["cy"]), clicks=1)
                    expanded_project = True
                    time.sleep(0.35)
                    shot0, info = macos.capture_window(app_name, focus=True)
                    items0 = macos.vision_ocr(shot0, info)
                    target = _find_sidebar_item(items0, agent_query, min_y=float(proj["cy"]) + 5.0)

            if target is None:
                sb_x = float(info["x"]) + 150.0
                sb_y = float(info["y"]) + float(info["height"]) * 0.55
                macos.cg_scroll(-10, sb_x, sb_y)
                time.sleep(0.30)
                shot0, info = macos.capture_window(app_name, focus=True)
                items0 = macos.vision_ocr(shot0, info)
                target = _find_sidebar_item(items0, agent_query)

            if target is None:
                sidebar_texts = [i["text"] for i in items0 if i["cx"] < SIDEBAR_MAX_X]
                raise RuntimeError(
                    f"Agent/thread '{agent_query}' not found in sidebar. Visible items: {sidebar_texts}"
                )

            macos.cg_click(float(info["x"]) + float(target["cx"]), float(info["y"]) + float(target["cy"]), clicks=1)
            time.sleep(0.40)

            shot_chat, info_chat = macos.capture_window(app_name, focus=True)
            items_chat = macos.vision_ocr(shot_chat, info_chat)

            send_meta: dict[str, Any] = {"sent": False}
            if isinstance(message, str) and message.strip():
                meta = paste_into_chat_input(info_chat, message, submit=submit, ocr_items=items_chat)
                send_meta = {"sent": True, "chars_sent": len(message), **meta}
                time.sleep(0.35)
                shot_chat, info_chat = macos.capture_window(app_name, focus=False)
                if read_reply:
                    items_chat = macos.vision_ocr(shot_chat, info_chat)

            main_text = ""
            if read_reply:
                main_text = "\n".join(i["text"] for i in items_chat if i["cx"] >= SIDEBAR_MAX_X)

            return {
                "ok": True,
                "action": "contact_agent",
                "silent_read_only": False,
                "agent_matched": target["text"],
                "expanded_project": expanded_project,
                "restored_user_context": restore_focus,
                **send_meta,
                "screenshot_path": str(shot_chat),
                "visible_main_text": main_text,
                "window": info_chat,
            }


CHATGPT_TOOLS: list[dict[str, Any]] = [
    {
        "name": "chatgpt_list_sidebar",
        "description": "Silently capture ChatGPT.app (zero focus steal or mouse movement) and list visible projects and running agent threads with coordinates.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "app_name": {"type": "string", "default": DEFAULT_APP},
                "focus": {"type": "boolean", "default": False},
            },
        },
    },
    {
        "name": "chatgpt_new_project_task",
        "description": "Start a brand-new task inside a specific ChatGPT.app project, paste & submit prompt, and restore user cursor & frontmost app. Serialized for Swarm safety.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "project_name": {"type": "string", "description": "Project name in sidebar (substring match)."},
                "prompt": {"type": "string", "description": "Initial task instruction to send."},
                "submit": {"type": "boolean", "default": True},
                "restore_focus": {"type": "boolean", "default": True},
                "app_name": {"type": "string", "default": DEFAULT_APP},
            },
            "required": ["project_name", "prompt"],
        },
    },
    {
        "name": "chatgpt_contact_agent",
        "description": "Contact or inspect an existing/running agent thread in ChatGPT.app. Read-only inspection on the open thread runs silently without touching focus or mouse.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "agent_query": {"type": "string", "description": "Thread/agent name in sidebar (substring match)."},
                "project_name": {"type": "string", "description": "Optional parent project name to expand if collapsed."},
                "message": {"type": "string", "description": "Optional follow-up message. Omit to inspect only."},
                "submit": {"type": "boolean", "default": True},
                "read_reply": {"type": "boolean", "default": True},
                "restore_focus": {"type": "boolean", "default": True},
                "app_name": {"type": "string", "default": DEFAULT_APP},
            },
            "required": ["agent_query"],
        },
    },
]

CHATGPT_HANDLERS = {
    "chatgpt_list_sidebar": tool_chatgpt_list_sidebar,
    "chatgpt_new_project_task": tool_chatgpt_new_project_task,
    "chatgpt_contact_agent": tool_chatgpt_contact_agent,
}
