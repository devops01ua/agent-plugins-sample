"""Read the hand-written files: the marketplace catalog and each plugin."""
import json
import re
from dataclasses import dataclass, field
from pathlib import Path

PREFIX = "ACME"
USER_CONFIG = re.compile(r"\$\{user_config\.([A-Za-z_][A-Za-z0-9_]*)\}")


@dataclass
class Plugin:
    name: str
    root: Path
    entry: dict
    manifest: dict
    servers: dict = field(default_factory=dict)

    @property
    def user_config(self):
        return self.manifest.get("userConfig", {})

    def env_name(self, key):
        return f"{PREFIX}_{self.name}_{key}".replace("-", "_").upper()

    def skills(self):
        base = self.root / "skills"
        if not base.is_dir():
            return []
        return sorted(d for d in base.iterdir() if (d / "SKILL.md").is_file())


def read_json(path):
    return json.loads(Path(path).read_text())


def load_marketplace(repo):
    return read_json(Path(repo) / ".claude-plugin" / "marketplace.json")


def load_plugins(repo):
    repo = Path(repo)
    plugins = []
    for entry in load_marketplace(repo)["plugins"]:
        root = (repo / entry["source"]).resolve()
        manifest = read_json(root / ".claude-plugin" / "plugin.json")
        mcp = root / ".mcp.json"
        servers = read_json(mcp)["mcpServers"] if mcp.is_file() else {}
        plugins.append(Plugin(entry["name"], root, entry, manifest, servers))
    return plugins


def substitute(value, replace):
    """Apply `replace` to every string inside a JSON-like value."""
    if isinstance(value, str):
        return replace(value)
    if isinstance(value, list):
        return [substitute(v, replace) for v in value]
    if isinstance(value, dict):
        return {k: substitute(v, replace) for k, v in value.items()}
    return value
