# Miche Platform

OS shell for operator home, floating island, inboxes, and app registry.

- **Repo:** Slimydog21/miche (this)
- **Killer app:** [Slimydog21/caffenagent](https://github.com/Slimydog21/caffenagent)
- **Spec:** `/Users/slimydog/specs/miche-platform`

## Quick start

```bash
uv sync
uv run pytest tests/test_miche_app_registry.py tests/test_miche_health_probe.py tests/test_miche_apps_routes.py -q
uv run miche  # dev server :8787
```

## MPLAT-SPR-01

- `interfaces/miche_app_registry.yaml` — install manifest
- `GET /api/platform/apps` — public registry
- `GET /api/platform/apps/{id}/health` — health probe

Do **not** implement platform home UI in caffenagent.