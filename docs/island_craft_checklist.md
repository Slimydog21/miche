# Island craft checklist — MPLAT-SPR-05

Operator-signed bar for PostHog-class craft (engineering quality, not brand copy).

| Check | Status | Notes |
|-------|--------|-------|
| 2px black border + 4px shadow on expanded panel | pass | `island.css` Lemon tokens |
| No full-page scrim on desktop | pass | Docked pill/panel only |
| Home inboxes scrollable beside island ≥1024px | pass | Fixed dock, no overlay |
| Composer min-height 44px touch target | pass | |
| Errors inline in thread (not toast-only) | pass | `miche-island__msg--error` |
| Cassette/dev banner when router fixture | pass | |
| Focus opens only via explicit CTA click | pass | No auto-redirect |
| Focus trap inside expanded panel | pass | Tab cycles within panel |
| Send ack shows router mode + app_id + latency + timestamp | pass | `formatAck()` in island.js |
| `prefers-reduced-motion` path | pass | CSS + no spring |
| JSONL utterance audit per send | pass | `logs/miche_island_utterance.jsonl` |
| No PostHog hedgehog / purple theme | pass | Miche mascot SVG |

**Signed:** automated gate pass · 2026-06-06 · operator visual review deferred to deploy