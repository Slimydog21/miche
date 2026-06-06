# Miche Platform v1 — decision record

**Status:** Accepted (capstone)  
**Date:** 2026-06-06  
**Sprint:** MPLAT-SPR-10

## What shipped

HTML spec at `/Users/slimydog/specs/miche-platform/` (10 sprints) executed via `/caffenagent` with worktree-per-sprint, merge-on-green, ≥2 critique rounds per sprint, and mechanical gates verbatim from each sprint page.

| Sprint | Theme | Merge (short) |
|--------|--------|---------------|
| MPLAT-SPR-01 | Registry + health + thesis | `2bc9d82` |
| MPLAT-SPR-02 | Home shell + Lemon tokens | `d3604f5` |
| MPLAT-SPR-03 | Action inbox | `2b3e398` |
| MPLAT-SPR-04 | Information inbox | `da2b19f` |
| MPLAT-SPR-05 | Floating island | `adbdf86` |
| MPLAT-SPR-06 | Intent router | `42ed79f` |
| MPLAT-SPR-07 | Focus bridge | `51a4ea9` |
| MPLAT-SPR-08 | Multi-tenant installs | `fcc010d` |
| MPLAT-SPR-09 | Mascot persona | `ed6e3c7` |
| MPLAT-SPR-10 | Platform capstone drill | (this merge) |

## Spec links

- **Platform shell:** [miche-platform index](/Users/slimydog/specs/miche-platform/index.html)
- **Device harness (complementary):** [project-miche index](/Users/slimydog/specs/project-miche/index.html)

## Capstone gate

```bash
bash harness/miche_platform_capstone_drill.sh --cassette
```

Exit 0 proves island-first triage → inline router card → inbox APIs → audit JSONL (`profile_id`, `router_decision_id`, `persona_render_id`) without live network.

## Operator sign-off

Pending human visual review of island + mascot on deploy; mechanical gates green on `main`.

## v2 follow-up

Hawkins hardening track: `/Users/slimydog/specs/miche-platform-v2/`. MPLAT2-SPR-01 fixes router mode honesty — see [router-mode-honesty.md](./router-mode-honesty.md).