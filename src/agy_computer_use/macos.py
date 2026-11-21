"""macOS system-level Computer Use primitives (zero third-party Python dependencies)."""

from __future__ import annotations

import contextlib
import ctypes
import fcntl
import json
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
BIN_DIR = REPO_ROOT / "bin"
VISION_OCR_BIN = BIN_DIR / "vision_ocr"
WIN_INFO_BIN = BIN_DIR / "win_info"

SHOT_DIR = Path(tempfile.gettempdir()) / "agy-computer-use"
LOCK_FILE = SHOT_DIR / "gui.lock"


# ---------------------------------------------------------------------------
# Low-level CoreGraphics bindings (64-bit safe)
# ---------------------------------------------------------------------------
class CGPoint(ctypes.Structure):
    _fields_ = [("x", ctypes.c_double), ("y", ctypes.c_double)]


_cg = ctypes.CDLL("/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics")
_cf = ctypes.CDLL("/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation")

_cg.CGEventCreateMouseEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint32, CGPoint, ctypes.c_uint32]
_cg.CGEventCreateMouseEvent.restype = ctypes.c_void_p

_cg.CGEventSetIntegerValueField.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_int64]
_cg.CGEventSetIntegerValueField.restype = None

_cg.CGEventPost.argtypes = [ctypes.c_uint32, ctypes.c_void_p]
_cg.CGEventPost.restype = None

_cg.CGEventCreateScrollWheelEvent.argtypes = [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_int32]
_cg.CGEventCreateScrollWheelEvent.restype = ctypes.c_void_p

_cf.CFRelease.argtypes = [ctypes.c_void_p]
_cf.CFRelease.restype = None

K_CG_HID_EVENT_TAP = 0
K_CG_EVENT_LEFT_MOUSE_DOWN = 1
K_CG_EVENT_LEFT_MOUSE_UP = 2
K_CG_EVENT_MOUSE_MOVED = 5
K_CG_MOUSE_BUTTON_LEFT = 0
K_CG_MOUSE_EVENT_CLICK_STATE = 1
K_CG_SCROLL_EVENT_UNIT_LINE = 1


def cg_move(x: float, y: float) -> None:
    ev = _cg.CGEventCreateMouseEvent(None, K_CG_EVENT_MOUSE_MOVED, CGPoint(x, y), K_CG_MOUSE_BUTTON_LEFT)
    if ev:
        _cg.CGEventPost(K_CG_HID_EVENT_TAP, ev)
        _cf.CFRelease(ev)


def cg_click(x: float, y: float, clicks: int = 1) -> None:
    pt = CGPoint(x, y)
    cg_move(x, y)
    time.sleep(0.03)
    for idx in range(1, max(1, clicks) + 1):
        down = _cg.CGEventCreateMouseEvent(None, K_CG_EVENT_LEFT_MOUSE_DOWN, pt, K_CG_MOUSE_BUTTON_LEFT)
        up = _cg.CGEventCreateMouseEvent(None, K_CG_EVENT_LEFT_MOUSE_UP, pt, K_CG_MOUSE_BUTTON_LEFT)
        if down:
            _cg.CGEventSetIntegerValueField(down, K_CG_MOUSE_EVENT_CLICK_STATE, idx)
            _cg.CGEventPost(K_CG_HID_EVENT_TAP, down)
            _cf.CFRelease(down)
        time.sleep(0.02)
        if up:
            _cg.CGEventSetIntegerValueField(up, K_CG_MOUSE_EVENT_CLICK_STATE, idx)
            _cg.CGEventPost(K_CG_HID_EVENT_TAP, up)
            _cf.CFRelease(up)
        time.sleep(0.03)


def cg_scroll(delta_y: int, x: float | None = None, y: float | None = None) -> None:
    if x is not None and y is not None:
        cg_move(x, y)
        time.sleep(0.03)
    ev = _cg.CGEventCreateScrollWheelEvent(None, K_CG_SCROLL_EVENT_UNIT_LINE, 1, int(delta_y))
    if ev:
        _cg.CGEventPost(K_CG_HID_EVENT_TAP, ev)
        _cf.CFRelease(ev)


# ---------------------------------------------------------------------------
# Locking, subprocess, AppleScript, clipboard & user-context restoration
# ---------------------------------------------------------------------------
@contextlib.contextmanager
def gui_lock():
    """Serialize GUI actions across concurrent AGY / Swarm workers."""
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    with open(LOCK_FILE, "w") as fp:
        fcntl.flock(fp.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(fp.fileno(), fcntl.LOCK_UN)


def run_cmd(args: list[str], input_text: str | None = None, timeout: int = 20) -> tuple[int, str, str]:
    p = subprocess.run(
        args,
        input=input_text,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return p.returncode, p.stdout, p.stderr


def escape_as(s: str) -> str:
    return s.replace("\\", "\\\\").replace('"', '\\"')


def run_osascript(script: str, lang: str = "AppleScript", timeout: int = 15) -> str:
    cmd = ["osascript"]
    if lang.lower() == "javascript":
        cmd += ["-l", "JavaScript"]
    cmd += ["-e", script]
    rc, out, err = run_cmd(cmd, timeout=timeout)
    if rc != 0:
        raise RuntimeError(err.strip() or f"osascript exited with code {rc}")
    return out.strip()


def get_clipboard() -> str:
    rc, out, _ = run_cmd(["pbpaste"], timeout=5)
    return out if rc == 0 else ""


def set_clipboard(text: str) -> None:
    rc, _, err = run_cmd(["pbcopy"], input_text=text, timeout=5)
    if rc != 0:
        raise RuntimeError(f"pbcopy failed: {err}")


def focus_app(app_name: str) -> None:
    safe = escape_as(app_name)
    run_osascript(f'tell application "{safe}" to activate')
    time.sleep(0.20)


def get_window_info(app_name: str, focus: bool = False) -> dict[str, Any]:
    if focus:
        focus_app(app_name)
    if WIN_INFO_BIN.exists():
        rc, out, _ = run_cmd([str(WIN_INFO_BIN), app_name], timeout=10)
        if rc == 0 and out.strip():
            return json.loads(out)
    safe = escape_as(app_name)
    jxa = f"""
    const se = Application("System Events");
    const procs = se.processes.whose({{name: "{safe}"}});
    if (procs.length === 0) {{
      JSON.stringify({{running: false, app: "{safe}"}});
    }} else {{
      const p = procs[0];
      const front = p.frontmost();
      const wins = p.windows();
      if (wins.length === 0) {{
        JSON.stringify({{running: true, app: "{safe}", frontmost: front, has_window: false}});
      }} else {{
        const w = wins[0];
        const pos = w.position();
        const sz = w.size();
        let title = "";
        try {{ title = w.name(); }} catch (e) {{}}
        JSON.stringify({{
          running: true,
          app: "{safe}",
          frontmost: front,
          has_window: true,
          title: title,
          x: pos[0],
          y: pos[1],
          width: sz[0],
          height: sz[1]
        }});
      }}
    }}
    """
    return json.loads(run_osascript(jxa, lang="JavaScript", timeout=10))


@contextlib.contextmanager
def preserve_user_context(app_name: str, restore: bool = True):
    """Snapshot cursor & frontmost app before an interactive GUI action, and restore immediately after."""
    snap = get_window_info(app_name, focus=False)
    orig_app = snap.get("frontmost_app") or ""
    orig_mx = snap.get("mouse_x")
    orig_my = snap.get("mouse_y")
    try:
        yield snap
    finally:
        if restore:
            if orig_mx is not None and orig_my is not None:
                try:
                    cg_move(float(orig_mx), float(orig_my))
                except Exception:
                    pass
            if orig_app and orig_app.lower() != app_name.lower():
                try:
                    focus_app(orig_app)
                except Exception:
                    pass


def capture_window(
    app_name: str, focus: bool = False, output_path: str | None = None
) -> tuple[Path, dict[str, Any]]:
    """Capture the target app window silently via CGWindowID (zero focus steal when focus=False)."""
    info = get_window_info(app_name, focus=focus)
    if not info.get("running") or not info.get("has_window"):
        raise RuntimeError(f"App '{app_name}' has no visible window: {info}")
    SHOT_DIR.mkdir(parents=True, exist_ok=True)
    out = Path(output_path) if output_path else (SHOT_DIR / f"shot_{int(time.time() * 1000)}.png")
    out.parent.mkdir(parents=True, exist_ok=True)

    wid = info.get("window_id")
    if wid is not None:
        rc, _, _ = run_cmd(["screencapture", "-x", "-o", "-l", str(wid), str(out)], timeout=15)
        if rc == 0 and out.exists():
            return out, info

    region = f"{int(info['x'])},{int(info['y'])},{int(info['width'])},{int(info['height'])}"
    rc, _, err = run_cmd(["screencapture", "-x", "-R", region, str(out)], timeout=15)
    if rc != 0:
        raise RuntimeError(
            f"screencapture failed (check macOS Screen Recording permission): {err.strip()}"
        )
    return out, info


def vision_ocr(img_path: Path, info: dict[str, Any]) -> list[dict[str, Any]]:
    if not VISION_OCR_BIN.exists():
        raise RuntimeError(f"Vision OCR binary not found at {VISION_OCR_BIN}. Run `make build` first.")
    rc, out, err = run_cmd(
        [str(VISION_OCR_BIN), str(img_path), str(info["width"]), str(info["height"])],
        timeout=15,
    )
    if rc != 0:
        raise RuntimeError(f"vision_ocr failed: {err.strip()}")
    return json.loads(out)


def paste_text_safe(text: str, submit: bool = True) -> None:
    """Paste text via clipboard with automatic restoration of previous clipboard contents."""
    prev_clip = get_clipboard()
    try:
        set_clipboard(text)
        time.sleep(0.08)
        run_osascript('tell application "System Events" to keystroke "v" using {command down}')
        time.sleep(0.20)
        if submit:
            run_osascript('tell application "System Events" to key code 36')
            time.sleep(0.15)
    finally:
        try:
            set_clipboard(prev_clip)
        except Exception:
            pass


def send_hotkey(app_name: str, key: str, modifiers: list[str] | None = None) -> None:
    mod_map = {
        "command": "command down",
        "cmd": "command down",
        "shift": "shift down",
        "option": "option down",
        "alt": "option down",
        "control": "control down",
        "ctrl": "control down",
    }
    as_mods = [mod_map[m.lower()] for m in (modifiers or []) if m.lower() in mod_map]
    special_codes = {
        "return": 36,
        "enter": 36,
        "escape": 53,
        "esc": 53,
        "tab": 48,
        "up": 126,
        "down": 125,
        "left": 123,
        "right": 124,
        "delete": 51,
        "backspace": 51,
    }
    focus_app(app_name)
    mod_clause = f" using {{{', '.join(as_mods)}}}" if as_mods else ""
    if key.lower() in special_codes:
        code = special_codes[key.lower()]
        run_osascript(f'tell application "System Events" to key code {code}{mod_clause}')
    else:
        safe_key = escape_as(key)
        run_osascript(f'tell application "System Events" to keystroke "{safe_key}"{mod_clause}')
