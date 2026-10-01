#!/usr/bin/env python3
"""Stop hook: after a session that used the GitOps status MCP, remind once to write
down what was found. It never blocks the session and never fails it."""
import json
import os
import sys
import tempfile
from pathlib import Path

MARKERS = ("gitops-prod", "gitops-test")
MESSAGE = (
    "acme-platform: this session looked at deployments. "
    "If you found something the team should know, write it down before you close it."
)


def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return
    if event.get("stop_hook_active"):
        return
    session = str(event.get("session_id") or "unknown")
    state_dir = Path(os.environ.get("CLAUDE_PLUGIN_DATA") or tempfile.gettempdir())
    seen = state_dir / f"acme-platform-reminded-{session}"
    if seen.exists():
        return
    transcript = event.get("transcript_path")
    try:
        text = Path(transcript).read_text(errors="ignore") if transcript else ""
    except OSError:
        return
    if not any(marker in text for marker in MARKERS):
        return
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        seen.touch()
    except OSError:
        pass
    print(json.dumps({"systemMessage": MESSAGE}))


if __name__ == "__main__":
    main()
