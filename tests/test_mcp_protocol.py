"""End-to-end MCP protocol and silent inspection smoke tests."""

from __future__ import annotations

import json
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SERVER_PY = REPO_ROOT / "src" / "agy_computer_use" / "server.py"


def _call_mcp(requests: list[dict]) -> list[dict]:
    payload = "\n".join(json.dumps(r) for r in requests) + "\n"
    p = subprocess.run(
        [sys.executable, str(SERVER_PY)],
        input=payload,
        capture_output=True,
        text=True,
        timeout=20,
    )
    if p.returncode != 0:
        raise AssertionError(f"server exited with {p.returncode}: {p.stderr}")
    return [json.loads(line) for line in p.stdout.strip().splitlines() if line.strip()]


class TestMcpProtocol(unittest.TestCase):
    def test_initialize_and_list_tools(self) -> None:
        responses = _call_mcp(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                {"jsonrpc": "2.0", "method": "notifications/initialized"},
                {"jsonrpc": "2.0", "id": 2, "method": "tools/list", "params": {}},
            ]
        )
        by_id = {r["id"]: r for r in responses if "id" in r}
        self.assertEqual(by_id[1]["result"]["serverInfo"]["name"], "agy-computer-use")
        names = {t["name"] for t in by_id[2]["result"]["tools"]}
        expected = {
            "chatgpt_list_sidebar",
            "chatgpt_new_project_task",
            "chatgpt_contact_agent",
            "gui_window_info",
            "gui_screenshot",
            "gui_send_message",
            "gui_read_ui_text",
            "gui_click",
            "gui_scroll",
            "gui_hotkey",
        }
        self.assertTrue(expected.issubset(names))

    def test_silent_window_info(self) -> None:
        responses = _call_mcp(
            [
                {"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {"protocolVersion": "2024-11-05"}},
                {
                    "jsonrpc": "2.0",
                    "id": 2,
                    "method": "tools/call",
                    "params": {"name": "gui_window_info", "arguments": {"app_name": "Finder", "focus": False}},
                },
            ]
        )
        by_id = {r["id"]: r for r in responses if "id" in r}
        self.assertFalse(by_id[2]["result"]["isError"])
        data = json.loads(by_id[2]["result"]["content"][0]["text"])
        self.assertEqual(data["app"], "Finder")
        self.assertIn("running", data)
        self.assertIn("frontmost_app", data)


if __name__ == "__main__":
    unittest.main()
