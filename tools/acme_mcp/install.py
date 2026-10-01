"""The messenger: put a plugin's MCP servers and skills into the config of a
tool that has no settings prompt of its own.

The paths below are the ones these tools used when this sample was written.
Check them against the tool's documentation before relying on them."""
import getpass
import json
import os
import re
import shutil
from pathlib import Path

from .model import USER_CONFIG, substitute

TOOLS = {
    "codex": {"config": ".codex/config.toml", "format": "toml", "skills": ".agents/skills", "copy": False},
    "antigravity": {"config": ".gemini/config/mcp_config.json", "format": "json", "skills": ".agents/skills", "copy": False},
    # Kiro does not load skills that are symlinks, so they are copied.
    "kiro": {"config": ".kiro/settings/mcp.json", "format": "json", "skills": ".kiro/skills", "copy": True},
}


def home():
    return Path(os.environ.get("ACME_HOME") or Path.home())


def resolve_settings(plugin, interactive=True, environ=None):
    """Value for every userConfig key: environment variable, then the default,
    then a prompt. Sensitive values are prompted for without echo."""
    environ = os.environ if environ is None else environ
    values = {}
    for key, spec in plugin.user_config.items():
        env_name = plugin.env_name(key)
        if environ.get(env_name):
            values[key] = environ[env_name]
            continue
        default = spec.get("default", "")
        if not interactive:
            values[key] = str(default)
            continue
        label = spec.get("title", key)
        if spec.get("sensitive"):
            values[key] = getpass.getpass(f"{label} (hidden, {env_name}): ")
        else:
            suffix = f" [{default}]" if default else ""
            values[key] = input(f"{label}{suffix}: ").strip() or str(default)
    return values


def render_servers(plugin, values):
    def replace(text):
        text = USER_CONFIG.sub(lambda m: values.get(m.group(1), ""), text)
        return text.replace("${CLAUDE_PLUGIN_ROOT}", str(plugin.root))

    servers = substitute(plugin.servers, replace)
    return {name: {k: v for k, v in s.items() if k != "type"} for name, s in servers.items()}


def write_private(path, text):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)
    path.chmod(0o600)  # the file now holds tokens


def merge_json(path, servers):
    data = json.loads(path.read_text()) if path.is_file() and path.read_text().strip() else {}
    data.setdefault("mcpServers", {}).update(servers)
    write_private(path, json.dumps(data, indent=2) + "\n")


def toml_key(key):
    return key if re.fullmatch(r"[A-Za-z0-9_-]+", key) else json.dumps(key)


def toml_tables(servers):
    lines = []
    for name, server in servers.items():
        lines.append(f"[mcp_servers.{toml_key(name)}]")
        lines.append(f"command = {json.dumps(server['command'])}")
        if server.get("args"):
            lines.append(f"args = {json.dumps(server['args'])}")
        if server.get("env"):
            lines.append("")
            lines.append(f"[mcp_servers.{toml_key(name)}.env]")
            for key, value in server["env"].items():
                lines.append(f"{toml_key(key)} = {json.dumps(value)}")
        lines.append("")
    return "\n".join(lines)


def merge_toml(path, servers):
    """Replace the tables of the servers we own, keep everything else as is."""
    owned = {f"mcp_servers.{toml_key(n)}" for n in servers}
    kept, skipping = [], False
    for line in (path.read_text().splitlines() if path.is_file() else []):
        header = re.fullmatch(r"\s*\[\[?([^\]]+)\]\]?\s*", line)
        if header:
            table = header.group(1).strip()
            skipping = any(table == o or table.startswith(o + ".") for o in owned)
        if not skipping:
            kept.append(line)
    body = "\n".join(kept).rstrip()
    write_private(path, (body + "\n\n" if body else "") + toml_tables(servers))


def install_skills(plugin, target, copy):
    target.mkdir(parents=True, exist_ok=True)
    done = []
    for skill in plugin.skills():
        dest = target / skill.name
        if dest.is_symlink() or dest.is_file():
            dest.unlink()
        elif dest.is_dir():
            shutil.rmtree(dest)
        if copy:
            shutil.copytree(skill, dest)
        else:
            dest.symlink_to(skill, target_is_directory=True)
        done.append(dest)
    return done


def install(plugin, tool, interactive=True, environ=None):
    spec = TOOLS[tool]
    servers = render_servers(plugin, resolve_settings(plugin, interactive, environ))
    config = home() / spec["config"]
    if servers:
        (merge_toml if spec["format"] == "toml" else merge_json)(config, servers)
    skills = install_skills(plugin, home() / spec["skills"], spec["copy"])
    return {"config": config, "servers": sorted(servers), "skills": skills}
