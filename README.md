# Miche Platform

OS shell for operator home, floating island, inboxes, and app registry.

- **Repo:** Slimydog21/miche (this)
- **Killer app:** [Slimydog21/caffenagent](https://github.com/Slimydog21/caffenagent)
- **Spec:** `/Users/slimydog/specs/miche-platform`

## Quick start

```bash
uv sync
npm ci
npx playwright install chromium
make check   # invariant gate: registry + pytest + e2e + capstone
uv run miche  # dev server :8787
```

## Invariant gate (MPLAT2-SPR-02)

```bash
bash scripts/check_platform.sh
# or: make check
```

Requires Node 20+, `uv`, and Playwright browsers (`npx playwright install chromium`).

## MPLAT-SPR-01

- `interfaces/miche_app_registry.yaml` — install manifest
- `GET /api/platform/apps` — public registry
- `GET /api/platform/apps/{id}/health` — health probe

Do **not** implement platform home UI in caffenagent.