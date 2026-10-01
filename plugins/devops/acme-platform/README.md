# acme-platform

A sample plugin with all three kinds of component:

- **MCP servers** `gitops-prod` and `gitops-test`: read-only, one per environment.
  They report rollout state and have no tool that changes anything: no sync,
  no apply, no rollback.
  The server is a mock bundled in `server/`, it answers from JSON fixtures and
  never opens a network connection. Tools: `whoami`, `list_applications`,
  `get_application`, `recent_events`.
- **Skill** `rollout-check`: a checklist for "is this rollout fine?" that uses
  the servers above.
- **Hook** on `Stop`: after a session that used the GitOps servers, reminds
  once to write down what was found.

## Install

```bash
claude plugin marketplace add https://github.com/devops01ua/agent-plugins-sample.git
claude plugin install acme-platform@acme
```

Then `/plugin configure acme-platform` inside a session. The URLs have
defaults; the tokens can stay empty, the mock does not need them.

Try it: "check the payments rollout in prod".

## Written by hand vs generated

| File | Written by |
| --- | --- |
| `.claude-plugin/plugin.json`, `.mcp.json`, `skills/`, `hooks/`, `server/` | a human |
| `plugin.json`, `mcp.json`, `.codex-plugin/plugin.json`, `codex.mcp.json` | `acme-mcp export` |
