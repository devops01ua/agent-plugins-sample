#!/usr/bin/env python3
"""Stop hook: after a session that edited infrastructure files, suggest once to
capture what was learned. It never blocks the session and never fails it."""
import json
import os
import re
import sys
import tempfile
from pathlib import Path

# An edit or write of an infrastructure file, as it appears in the transcript.
INFRA_EDIT = re.compile(
    r'"name":\s*"(?:Edit|Write|MultiEdit)".{0,400}?"file_path":\s*"[^"]*'
    r'(?:\.tf|\.tfvars|\.ya?ml|Dockerfile|\.gitlab-ci\.yml|Jenkinsfile)"',
    re.S,
)
MESSAGE = (
    "acme-knowledge: this session changed infrastructure files. If you learned something "
    "the team should know (a quirk, a decision, an incident), say \"capture this\"."
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
    seen = state_dir / f"acme-knowledge-nudged-{session}"
    if seen.exists():
        return
    transcript = event.get("transcript_path")
    try:
        text = Path(transcript).read_text(errors="ignore") if transcript else ""
    except OSError:
        return
    if not INFRA_EDIT.search(text):
        return
    try:
        state_dir.mkdir(parents=True, exist_ok=True)
        seen.touch()
    except OSError:
        pass
    print(json.dumps({"systemMessage": MESSAGE}))


if __name__ == "__main__":
    main()
