# Miche router modes (MPLAT2-SPR-01)

| `router_mode` | When | Implementation |
|---------------|------|----------------|
| `cassette` | `MICHE_ROUTER_FIXTURE=cassette` or `MICHE_ISLAND_ROUTER_FIXTURE=cassette` | Locked substring fixtures for offline tests |
| `rules_v0` | Default production (no cassette env) | Registry-constrained keyword classifier in `dispatch.py` |
| `inbox_fallback` | `rules_v0` cannot classify (e.g. "what is blocked") | Action inbox triage via `_blocked_inbox_decision` |
| `error` | Capability resolution failure in island adapter | No fake success |

**Removed (v1 honesty debt):** `MICHE_ROUTER_LLM_API_KEY` and `router_mode=llm` — no model was ever called. Future LLM routing requires a new spec and explicit `router_mode=llm` only when a model API is invoked.