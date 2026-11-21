.PHONY: build test install-mcp clean

ROOT := $(CURDIR)

build:
	@mkdir -p $(ROOT)/bin
	swiftc -O $(ROOT)/native/vision_ocr.swift -o $(ROOT)/bin/vision_ocr
	swiftc -O $(ROOT)/native/win_info.swift -o $(ROOT)/bin/win_info
	@echo "Built native helpers in $(ROOT)/bin"

test: build
	PYTHONPATH=$(ROOT)/src python3 -m unittest discover -s $(ROOT)/tests -v

install-mcp: build
	python3 -c 'import json, pathlib; p = pathlib.Path.home() / ".gemini/config/mcp_config.json"; p.parent.mkdir(parents=True, exist_ok=True); data = json.loads(p.read_text()) if p.exists() else {}; servers = data.setdefault("mcpServers", {}); servers.pop("chatgpt-gui-bridge", None); servers["agy-computer-use"] = {"command": "/usr/bin/env", "args": ["python3", "$(ROOT)/src/agy_computer_use/server.py"], "env": {"PYTHONPATH": "$(ROOT)/src"}}; p.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n"); print("Updated", p)'

clean:
	rm -rf $(ROOT)/bin
