"""The scribes: generate the native manifests of the other tools from the
hand-written Claude Code files. Generated files carry a marker and are never
edited by hand; `export --check` fails when one drifts from its source."""
import json
from pathlib import Path

from .model import USER_CONFIG, load_marketplace, load_plugins, substitute

MARKER = "acme-mcp export"
EXTENSION = "ua.devops01.acme"
SCHEMA = "https://agent-plugins.org/schemas/1.0.0"


def to_env_refs(plugin, servers):
    return substitute(
        servers, lambda s: USER_CONFIG.sub(lambda m: "${" + plugin.env_name(m.group(1)) + "}", s)
    )


def plugin_files(plugin):
    manifest = plugin.manifest
    base = {
        "name": manifest["name"],
        "version": manifest["version"],
        "description": manifest["description"],
        "author": manifest["author"],
        "keywords": plugin.entry.get("keywords", []),
        "x-generated-by": MARKER,
    }
    servers = to_env_refs(plugin, plugin.servers)
    files = {}

    portable = {"$schema": f"{SCHEMA}/plugin.schema.json", **base}
    if plugin.user_config:
        portable["extensions"] = {
            EXTENSION: {
                "userConfig": plugin.user_config,
                "env": {key: plugin.env_name(key) for key in plugin.user_config},
            }
        }
    files["plugin.json"] = portable

    codex = dict(base)
    if servers:
        files["mcp.json"] = {
            "$schema": f"{SCHEMA}/mcp.schema.json",
            "x-generated-by": MARKER,
            "mcpServers": servers,
        }
        files["codex.mcp.json"] = {
            "x-generated-by": MARKER,
            "mcpServers": {
                name: {k: v for k, v in server.items() if k != "type"}
                for name, server in servers.items()
            },
        }
        codex["mcpServers"] = "./codex.mcp.json"
    files[".codex-plugin/plugin.json"] = codex
    return files


def all_files(repo):
    """Every generated file as {absolute path: text}."""
    repo = Path(repo)
    out = {}
    plugins = load_plugins(repo)
    for plugin in plugins:
        for rel, data in plugin_files(plugin).items():
            out[plugin.root / rel] = json.dumps(data, indent=2) + "\n"
    market = load_marketplace(repo)
    catalog = {
        "name": market["name"],
        "interface": {"displayName": market.get("description", market["name"])},
        "x-generated-by": MARKER,
        "plugins": [
            {
                "name": p.name,
                "source": {"source": "local", "path": p.entry["source"]},
                "category": p.entry.get("category", "other"),
                "policy": {"installation": "AVAILABLE"},
            }
            for p in plugins
        ],
    }
    out[repo / ".agents" / "plugins" / "marketplace.json"] = json.dumps(catalog, indent=2) + "\n"
    return out


def export(repo, check=False):
    """Write the generated files, or with check=True only report drift.
    Returns the list of paths that are missing or differ."""
    stale = []
    for path, text in all_files(repo).items():
        if path.is_file() and path.read_text() == text:
            continue
        stale.append(path)
        if not check:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text)
    return stale
