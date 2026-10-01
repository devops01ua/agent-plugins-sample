#!/usr/bin/env bash
# The gatekeeper: every check in one run. CI runs the same script.
set -uo pipefail
cd "$(dirname "$0")/.."

fail=0
run() {
  local label="$1"; shift
  echo "-- ${label}"
  if "$@"; then echo "ok   ${label}"; else echo "FAIL ${label}"; fail=1; fi
}

run "generated manifests are fresh" env PYTHONPATH=tools python3 -m acme_mcp export --check
run "tests" python3 -m unittest discover -s tests -q

if command -v claude >/dev/null 2>&1; then
  run "claude plugin validate: marketplace" claude plugin validate .
  for manifest in plugins/*/*/.claude-plugin/plugin.json; do
    plugin="$(dirname "$(dirname "$manifest")")"
    run "claude plugin validate: ${plugin}" claude plugin validate "$plugin"
  done
else
  echo "-- claude CLI not found, skipping claude plugin validate"
fi

if [ "$fail" -eq 0 ]; then echo "ALL CHECKS PASSED"; else echo "SOME CHECKS FAILED"; fi
exit "$fail"
