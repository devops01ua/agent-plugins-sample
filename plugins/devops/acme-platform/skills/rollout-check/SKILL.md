---
name: rollout-check
description: Check a rollout before and after it ships. Use when the user asks
  whether a rollout is safe, why a rollout is stuck, or to verify a release in
  prod or test. Reads sync state and recent events through the GitOps status MCP.
---

# Rollout check

Read-only: this skill looks and reports. It never changes anything.

1. Ask which environment if the user did not say. Never assume prod.
2. Use the `gitops-<env>` MCP server: `list_applications` when no application
   was named, otherwise `get_application`.
3. Compare the desired and the live revision. If they differ, say so first.
4. Call `recent_events` and read them oldest to newest.
5. Report in this shape:
   - State: sync and health, one line
   - Differences: desired vs live revision, or "none"
   - Events: the last five, as they are
   - Next step: one suggestion, or "nothing to do"

If the server is not connected, say that the acme-platform plugin needs its
settings (`/plugin configure acme-platform`) instead of guessing.
