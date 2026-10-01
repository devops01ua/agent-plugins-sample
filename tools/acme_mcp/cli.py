import argparse
import os
import subprocess
import sys
from pathlib import Path

from . import export as export_mod
from . import install as install_mod
from .model import load_plugins

DEFAULT_URL = "https://github.com/devops01ua/agent-plugins-sample.git"


def checkout_dir():
    return Path(os.environ.get("ACME_MARKETPLACE_HOME") or Path.home() / ".acme-plugins")


def find_repo(arg):
    for candidate in (arg, os.environ.get("ACME_MARKETPLACE_HOME"), Path.cwd(), checkout_dir()):
        if candidate and (Path(candidate) / ".claude-plugin" / "marketplace.json").is_file():
            return Path(candidate).resolve()
    sys.exit("no marketplace found: run `acme-mcp sync` first, or pass --repo PATH")


def pick(plugins, name):
    for plugin in plugins:
        if plugin.name == name:
            return plugin
    sys.exit(f"unknown plugin {name!r}; known: {', '.join(p.name for p in plugins)}")


def cmd_sync(args):
    dest = checkout_dir()
    if (dest / ".git").is_dir():
        subprocess.run(["git", "-C", str(dest), "pull", "--ff-only"], check=True)
    else:
        subprocess.run(["git", "clone", args.url, str(dest)], check=True)
    print(f"marketplace checkout: {dest}")


def cmd_list(args):
    for plugin in load_plugins(find_repo(args.repo)):
        print(f"{plugin.name} {plugin.manifest['version']}")
        print(f"  servers: {', '.join(plugin.servers) or '-'}")
        print(f"  skills:  {', '.join(s.name for s in plugin.skills()) or '-'}")
        for key, spec in plugin.user_config.items():
            kind = "secret" if spec.get("sensitive") else "setting"
            print(f"  {kind}: {key} -> {plugin.env_name(key)}")


def cmd_env(args):
    plugin = pick(load_plugins(find_repo(args.repo)), args.plugin)
    for key, spec in plugin.user_config.items():
        value = "" if spec.get("sensitive") else spec.get("default", "")
        print(f'export {plugin.env_name(key)}="{value}"')


def cmd_export(args):
    repo = find_repo(args.repo)
    stale = export_mod.export(repo, check=args.check)
    for path in stale:
        print(("STALE " if args.check else "wrote ") + str(path.relative_to(repo)))
    if args.check and stale:
        print("generated files drifted from their source: run `acme-mcp export`", file=sys.stderr)
        return 1
    if not stale:
        print("generated files are fresh")
    return 0


def cmd_install(args):
    plugin = pick(load_plugins(find_repo(args.repo)), args.plugin)
    result = install_mod.install(plugin, args.tool, interactive=not args.no_input)
    print(f"{plugin.name} -> {args.tool}")
    print(f"  servers {', '.join(result['servers']) or '-'} in {result['config']}")
    for skill in result["skills"]:
        print(f"  skill   {skill}")


def main(argv=None):
    parser = argparse.ArgumentParser(prog="acme-mcp", description=__doc__)
    parser.add_argument("--repo", help="path to a marketplace checkout")
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("sync", help="clone or update the marketplace checkout")
    p.add_argument("--url", default=DEFAULT_URL)
    p.set_defaults(func=cmd_sync)

    p = sub.add_parser("list", help="plugins, their servers, skills and settings")
    p.set_defaults(func=cmd_list)

    p = sub.add_parser("env", help="print export lines for a plugin's settings")
    p.add_argument("plugin")
    p.set_defaults(func=cmd_env)

    p = sub.add_parser("export", help="generate the native manifests")
    p.add_argument("--check", action="store_true", help="fail if a generated file is stale")
    p.set_defaults(func=cmd_export)

    p = sub.add_parser("install", help="install a plugin into another tool's config")
    p.add_argument("plugin")
    p.add_argument("--tool", required=True, choices=sorted(install_mod.TOOLS))
    p.add_argument("--no-input", action="store_true", help="never prompt, use env vars and defaults")
    p.set_defaults(func=cmd_install)

    args = parser.parse_args(argv)
    return args.func(args) or 0
