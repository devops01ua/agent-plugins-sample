# agent-plugins-sample

A sample **team plugin marketplace for coding agents**: one git repository as
the source of truth, one plugin format written by hand, native manifests for
the other tools generated from it, and a gate that fails when they drift.

It is the companion repo of the article "The Tower of Babylon, or How We
Shipped One Plugin to Four Coding Agents". Everything here is a sample: the
names are made up and the GitOps server is a mock.

## What is inside

```text
.claude-plugin/marketplace.json      the catalog, written by hand
.agents/plugins/marketplace.json     generated catalog for Codex
plugins/devops/acme-platform/        the sample plugin (MCP + skill + hook)
plugins/devops/acme-knowledge/       wires the agent to the shared knowledge repo (skill + hook)
tools/acme_mcp/                      export (the scribes) and install (the messenger)
scripts/check.sh                     the gatekeeper, also run in CI
tests/                               tests for the export, the installer, the server and the hook
```

## Try it in Claude Code

```bash
claude plugin marketplace add https://github.com/devops01ua/agent-plugins-sample.git
claude plugin install acme-platform@acme
```

Inside a session run `/plugin configure acme-platform` (the defaults are fine,
the tokens can stay empty), then ask: "check the payments rollout in prod".

The `.git` suffix matters: without it the URL is read as a link to a single
marketplace file.

## The knowledge half

The tools are one half. The other half is what the agents know: a shared knowledge repo,
[agent-knowledge-sample](https://github.com/devops01ua/agent-knowledge-sample). The
`acme-knowledge` plugin wires the agent to it:

```bash
claude plugin install acme-knowledge@acme
```

Then ask: "set up the knowledge repo".

## Other tools

Codex can read the generated catalog directly:

```bash
codex plugin marketplace add https://github.com/devops01ua/agent-plugins-sample.git
```

For tools without a settings prompt there is a small installer:

```bash
uv tool install git+https://github.com/devops01ua/agent-plugins-sample.git
acme-mcp sync                                   # clone or update ~/.acme-plugins
acme-mcp list                                   # plugins, servers, skills, settings
acme-mcp install --tool codex acme-platform     # or --tool kiro, --tool antigravity
```

`acme-mcp install` asks for the settings (secrets without echo), merges the
servers into the tool's own config file, replaces servers with the same name
and keeps the rest, and links the skills (copies them for Kiro, which does not
load symlinked skills). The config file is set to mode 600 because it now
holds tokens. Settings can also come from environment variables named
`ACME_<PLUGIN>_<KEY>`; `acme-mcp env acme-platform` prints them.

| Tool | Servers go to | Skills go to |
| --- | --- | --- |
| Codex | `~/.codex/config.toml` | `~/.agents/skills` (links) |
| Antigravity | `~/.gemini/config/mcp_config.json` | `~/.agents/skills` (links) |
| Kiro | `~/.kiro/settings/mcp.json` | `~/.kiro/skills` (copies) |

Pick one path per tool. Adding the marketplace natively and also running the
installer gives you every server twice.

> The installer is covered by tests against a temporary home directory. It was
> not run against live Codex, Kiro or Antigravity installs, and those tools
> change their config locations between versions. Check the paths above
> against the tool's documentation before relying on them.

## Write once, generate the rest

Edit only the hand-written files, then:

```bash
PYTHONPATH=tools python3 -m acme_mcp export     # regenerate
./scripts/check.sh                              # the gate
```

What changes between the dialects is mostly how a setting reaches a server:

```json
"GITOPS_API_TOKEN": "${user_config.prod_token}"            // written by hand
"GITOPS_API_TOKEN": "${ACME_ACME_PLATFORM_PROD_TOKEN}"     // generated
```

Generated files carry `"x-generated-by": "acme-mcp export"`. Never edit them:
`export --check` compares each one with what the source would produce, and CI
is red when they differ.

## Adding a plugin

1. Create `plugins/<category>/<name>/` with `.claude-plugin/plugin.json` and
   the components you need (`.mcp.json`, `skills/`, `hooks/`).
2. Add one entry to `.claude-plugin/marketplace.json`. Keep the entry name and
   the manifest name the same.
3. Run the export and the gate.

Rules worth copying into your own marketplace:

- pin server versions, no `@latest`
- read-only by default; write access is a separate decision
- tokens are `sensitive` settings, never values in the repository
- guidance goes in a skill, behaviour that must always happen goes in a hook

## Documentation

- Claude Code: https://code.claude.com/docs/en/plugins/create-marketplace
- Codex: https://developers.openai.com/plugins/build/plugins
- Kiro: https://kiro.dev/docs/powers/create/
- Antigravity: https://antigravity.google/docs/plugins/
- Agent Skills: https://agentskills.io/specification
- MCP: https://modelcontextprotocol.io

## License

MIT
