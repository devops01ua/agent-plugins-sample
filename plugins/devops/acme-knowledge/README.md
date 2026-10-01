# acme-knowledge

Connects the agent to the team's shared knowledge repo,
[agent-knowledge-sample](https://github.com/devops01ua/agent-knowledge-sample).

- **Skill** `kb-setup`: installs the `acme-kb` CLI, clones the knowledge repo and links
  its five skills (knowledge, capture, ingest, lint, start-task).
- **Hook** on `Stop`: after a session that edited infrastructure files (Terraform, YAML,
  Dockerfile, CI config), suggests once to capture what was learned.

The knowledge itself never lives in this plugin. The plugin only wires the agent to the
repo, which is read in place and changed through pull requests.

## Install

```bash
claude plugin marketplace add https://github.com/devops01ua/agent-plugins-sample.git
claude plugin install acme-knowledge@acme
```

Then ask: "set up the knowledge repo".

## Written by hand vs generated

| File | Written by |
| --- | --- |
| `.claude-plugin/plugin.json`, `skills/`, `hooks/` | a human |
| `plugin.json`, `.codex-plugin/plugin.json` | `acme-mcp export` |

The hook is Claude Code only. On the other tools, ask for a capture by hand at the end
of a session.
