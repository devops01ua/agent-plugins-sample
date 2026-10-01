---
name: kb-setup
description: Set up or repair the team's knowledge layer on this machine. Use when
  acme-kb is not installed, when the knowledge, capture, ingest, lint or start-task
  skills are missing, when the user says set up the knowledge repo or install acme-kb,
  or when a command fails with "not inside a knowledge repo".
---

# Knowledge setup

1. Check what is there: `acme-kb --help` and `ls ~/.acme-knowledge`.
2. If the CLI is missing, install it:
   `uv tool install git+https://github.com/devops01ua/agent-knowledge-sample.git`
3. Run `acme-kb setup`. It clones the knowledge repo to `~/.acme-knowledge` (or pulls
   it) and links its skills into `~/.claude/skills` and `~/.agents/skills`.
4. Verify with `acme-kb search token`: it should print at least one record.
5. Tell the user which skills are now available (knowledge, capture, ingest, lint,
   start-task) and that new skills load in the next session.

Do not copy records out of the knowledge repo into the project. The repo is read in
place and changed only through pull requests.
