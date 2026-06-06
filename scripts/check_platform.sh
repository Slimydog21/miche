#!/usr/bin/env bash
# MPLAT2-SPR-02 — invariant platform gate bundle (local Hawkins spine).
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "${CHECK_PLATFORM_DRY_RUN:-}" == "1" ]]; then
  echo "check_platform: DRY_RUN — steps only"
  echo "  1 registry"
  echo "  2 pytest-full"
  echo "  3 playwright-island"
  echo "  4 capstone-cassette"
  exit 0
fi

step() { echo "check_platform: $1"; }

step "1 — registry contract"
uv run python scripts/check_platform_registry.py

step "2 — pytest full suite"
uv run pytest -q

step "3 — playwright island e2e"
if [[ ! -d node_modules ]]; then
  echo "check_platform: installing npm deps (npm ci)" >&2
  npm ci
fi
if ! command -v npx >/dev/null 2>&1; then
  echo "check_platform: npx not found — install Node.js 20+" >&2
  exit 1
fi
if ! npx playwright --version >/dev/null 2>&1; then
  echo "check_platform: run 'npx playwright install chromium' before check" >&2
  exit 1
fi
export MICHE_ROUTER_FIXTURE=cassette
export MICHE_ISLAND_ROUTER_FIXTURE=cassette
npm run test:e2e:island

step "4 — capstone drill (--cassette)"
export MICHE_ROUTER_FIXTURE=cassette
export MICHE_ISLAND_ROUTER_FIXTURE=cassette
bash harness/miche_platform_capstone_drill.sh --cassette

echo "check_platform: OK"