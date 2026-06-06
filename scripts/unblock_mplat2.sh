#!/usr/bin/env bash
# Auto-unblock MPLAT2-SPR-03–07 when agent shell is degraded.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
MARKER="/Users/slimydog/specs/miche-platform-v2/.caffenagent/RUN_UNBLOCK"
LOCK="/Users/slimydog/specs/miche-platform-v2/.caffenagent/RUN_UNBLOCK.lock"
LOG="/Users/slimydog/specs/miche-platform-v2/.caffenagent/unblock.log"

exec >>"$LOG" 2>&1
echo "=== unblock_mplat2 $(date -u +%Y-%m-%dT%H:%M:%SZ) ==="

[[ -f "$MARKER" ]] || { echo "no marker; skip"; exit 0; }
if [[ -f "$LOCK" ]]; then echo "lock held; skip"; exit 0; fi
touch "$LOCK"
trap 'rm -f "$LOCK"' EXIT
rm -f "$MARKER"

export MICHE_ROUTER_FIXTURE=cassette
export MICHE_ISLAND_ROUTER_FIXTURE=cassette

if ! git diff --quiet || ! git diff --cached --quiet; then
  uv run pytest -q
  npm ci
  npx playwright install chromium
  bash scripts/check_platform.sh
  git add -A
  git commit -m "feat(platform): MPLAT2-SPR-03–07 Hawkins hardening (CI, golden E2E, craft, capstone v2)"
  echo "commit_sha=$(git rev-parse HEAD)"
fi

echo "unblock_mplat2: done"