# Orchestration UI — decision record

**Status:** Accepted  
**Date:** 2026-06-12  
**Commits:** `e72efa5` (miche), `f0b73c8` + `da60aad` (caffenagent)  
**Spec:** `/Users/slimydog/specs/miche-orchestration-ui/`

## Context

The Miche platform needed a native UI for orchestrating CLI agents (Claude Code, Grok Build, MiMo Code) via the caffenagent backend. The caffenagent backend already had 50+ HTTP API endpoints covering sessions, studio, agents, voice, gaps, routing, workstation, memory, handoffs, and execution graphs. But the only way to use them was through caffenagent's own web UI (separate port, HTTPBasic auth) or the CLI.

## Decision

**Build a Miche-native orchestration dashboard at `/orchestrate`** — not an iframe of caffenagent's UI, not a standalone caffenagent page.

### Why not iframe (rejected alternative)

Egghead-2 investigation confirmed Focus mode's iframe architecture is fundamentally incompatible with multi-agent monitoring:
- Sandbox blocks parent-child coordination (no DOM manipulation, no state sharing)
- No JS runtime in the iframe context
- Single-app routing (Focus is `/focus/{app_id}` — one app, one view)
- Stateless handoff token (24h TTL, one-shot navigation)

### Why not caffenagent-only (rejected alternative)

Violates the Miche platform thesis: "Do not implement platform home UI in caffenagent." The orchestration dashboard is a platform surface that needs cross-app state (multiple agents, multiple projects).

## What was built

| Route | Purpose |
|---|---|
| `/orchestrate` | Dashboard — project grid, agent lifecycle, create form |
| `/orchestrate/graph` | Execution graph timeline |
| `/orchestrate/studio` | Session studio |
| `/orchestrate/pr-queue` | PR queue viewer |
| `/orchestrate/gaps` | Gap analysis |
| `/orchestrate/metrics` | Agent performance metrics |
| `/orchestrate/specs` | HTML spec browser |
| `/orchestrate/voice` | Voice cascade viewer |
| `/orchestrate/memory` | Memory query |
| `/orchestrate/workstation` | PTY pane viewer |
| `/orchestrate/connectors` | Connector blocks |
| `/orchestrate/settings` | Config status |

Infrastructure:
- API proxy (`/api/caffenagent/*`) with server-side auth, 10MB body limit, sanitized errors
- 7 island voice commands for agent orchestration
- Shared `utils.js` (escapeHtml, timeAgo, renderMarkdownSafe)
- Polling with exponential backoff (5s normal, 15s after 3 errors)
- PTY lifecycle bridge (`PanePty.poll()` + `pane_monitor.py`)

## Tests

- 198 pytest + 9 E2E + 11 island E2E = **218 tests pass**
- Invariant gate (`make check`): ALL GREEN
- 6 adversarial critique rounds, 0 BLOCKING defects remaining

## Critique rounds

| Round | Focus | Verdict |
|---|---|---|
| 1 | Initial build | MERGE |
| 2 | Deep critique | SEND BACK → form protection, CSS.escape, JSON-before-ok |
| 3 | Edge cases | SEND BACK → orphaned code, XSS, NaN stale |
| 4 | Proxy security | MERGE → body limit, error sanitization |
| 5 | Taste audit | SEND BACK → undefined CSS tokens, dead CSS |
| 6 | Integration | SEND BACK → backoff recovery reset |

## What would change this decision

- Caffenagent ships a postMessage bridge that solves iframe↔island coordination
- SSE/WebSocket endpoints added to caffenagent (replaces polling)
- The two-repo model is abandoned (Miche merges into caffenagent)

## Related docs

- `docs/miche_platform_thesis.md`
- `docs/naming_canon.yaml`
- `/Users/slimydog/specs/miche-orchestration-ui/index.html`
