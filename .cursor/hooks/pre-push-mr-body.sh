#!/usr/bin/env bash
# Cursor hook: refresh MR_BODY.md before git push, then allow the command.
set -uo pipefail

ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$ROOT" || exit 0

if command -v make >/dev/null 2>&1; then
  make mr_body >/dev/null 2>&1 || true
fi

echo '{ "permission": "allow" }'
exit 0
