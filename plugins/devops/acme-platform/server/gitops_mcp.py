#!/usr/bin/env python3
"""A tiny read-only MCP server over stdio, standard library only.

It reports rollout state. It has no tool that changes anything: no sync, no
apply, no rollback. An agent may look at production, never touch it.

It is a mock: it answers from the JSON fixtures next to this file and never
opens a network connection. It exists so the sample plugin runs on any laptop
with python3. In a real marketplace this is where a pinned public server goes,
for example `npx -y some-gitops-mcp@1.4.2 stdio`.
"""
import json
import os
import sys
from pathlib import Path

ENV = os.environ.get("GITOPS_ENV", "test")
BASE_URL = os.environ.get("GITOPS_BASE_URL", "")
TOKEN_SET = bool(os.environ.get("GITOPS_API_TOKEN"))
READ_ONLY = os.environ.get("MCP_READ_ONLY", "true").lower() == "true"
DEFAULT_PROTOCOL = "2025-06-18"

NAME_ARG = {
    "type": "object",
    "properties": {"name": {"type": "string", "description": "Application name"}},
    "required": ["name"],
}
TOOLS = [
    {
        "name": "whoami",
        "description": "Show which environment and base URL this server is configured for, and whether a token was provided.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "list_applications",
        "description": "List applications with their sync and health state.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    {
        "name": "get_application",
        "description": "Desired and live revision, sync and health state of one application.",
        "inputSchema": NAME_ARG,
    },
    {
        "name": "recent_events",
        "description": "The most recent rollout events of one application, oldest first.",
        "inputSchema": NAME_ARG,
    },
]


def load_apps():
    fixture = Path(__file__).parent / "fixtures" / f"{ENV}.json"
    return json.loads(fixture.read_text())["applications"]


def find_app(name):
    for app in load_apps():
        if app["name"] == name:
            return app
    known = ", ".join(a["name"] for a in load_apps())
    raise ValueError(f"no application named {name!r} in {ENV}; known: {known}")


def call_tool(name, args):
    if name == "whoami":
        return {
            "environment": ENV,
            "base_url": BASE_URL,
            "token": "set" if TOKEN_SET else "not set",
            "read_only": READ_ONLY,
            "note": "mock server, answers come from bundled fixtures",
        }
    if name == "list_applications":
        return [{k: a[k] for k in ("name", "sync", "health")} for a in load_apps()]
    if name == "get_application":
        app = find_app(args.get("name", ""))
        return {k: v for k, v in app.items() if k != "events"}
    if name == "recent_events":
        return find_app(args.get("name", ""))["events"][-5:]
    raise ValueError(f"unknown tool {name!r}")


def handle(msg):
    method = msg.get("method")
    params = msg.get("params") or {}
    if method == "initialize":
        return {
            "protocolVersion": params.get("protocolVersion", DEFAULT_PROTOCOL),
            "capabilities": {"tools": {}},
            "serverInfo": {"name": f"acme-gitops-{ENV}", "version": "0.1.0"},
        }
    if method == "ping":
        return {}
    if method == "tools/list":
        return {"tools": TOOLS}
    if method == "tools/call":
        try:
            result = call_tool(params.get("name"), params.get("arguments") or {})
            return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}
        except ValueError as exc:
            return {"content": [{"type": "text", "text": str(exc)}], "isError": True}
    raise LookupError(method)


def main():
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError:
            continue
        if "id" not in msg:  # a notification, nothing to answer
            continue
        reply = {"jsonrpc": "2.0", "id": msg["id"]}
        try:
            reply["result"] = handle(msg)
        except LookupError:
            reply["error"] = {"code": -32601, "message": f"method not found: {msg.get('method')}"}
        sys.stdout.write(json.dumps(reply) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
