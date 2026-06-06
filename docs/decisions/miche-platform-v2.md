# Miche Platform v2 — decision record

**Status:** Accepted (Hawkins capstone)  
**Date:** 2026-06-06  
**Spec:** `/Users/slimydog/specs/miche-platform-v2/`

## Prerequisite

v1 (MPLAT-SPR-01–10) on `main` @ `9d3515c`.

## What v2 shipped

| Sprint | Theme | Merge |
|--------|--------|-------|
| MPLAT2-SPR-01 | Router mode honesty | `d9167a3` |
| MPLAT2-SPR-02 | `check_platform.sh` + `make check` | `87796b0` |
| MPLAT2-SPR-03 | GitHub Actions `platform.yml` | pending commit |
| MPLAT2-SPR-04 | `golden_path.spec.ts` | pending commit |
| MPLAT2-SPR-05 | Craft checklist + sign-off | pending commit |
| MPLAT2-SPR-06 | Capstone v2 + rules smoke | pending commit |
| MPLAT2-SPR-07 | This decision + critic rung 1 | pending commit |

**CI:** https://github.com/Slimydog21/miche/actions/workflows/platform.yml (green after push)

## Invariant gate

```bash
bash scripts/check_platform.sh
```

## Honest deferrals

- **Real LLM router** — not v2; requires future spec with model calls + structured output.
- **Device E2E** — remains in `project-miche`.

## What would prove v2 wrong

- CI green but golden_path fails on deploy (DOM/API drift).
- `router_mode=llm` reappears without model implementation.
- Operator craft sign-off revoked after visual review on production.