# Miche Platform thesis

**Status:** canonical · MPLAT-SPR-01  
**Repos:** two-repo model — platform shell in **miche**, killer app in **caffenagent**.

## Do not merge into caffenagent

Platform home, floating island, inboxes, and app registry live in the **miche** repo. The `caffenagent/` Python package in Slimydog21/caffenagent remains the session/htmlspec/PRcrouch engine. Folding platform shell code into caffenagent breaks friend self-host installs and violates the operator split decided 2026-06-05.

## Island-first, Focus when depth needs chrome

| Situation | Surface |
|-----------|---------|
| Triage, dispatch, capture, status | **Miche home** + floating island |
| Dense review, multi-pane grind, flow state | **Focus mode** (full app chrome) |

Aligned with `docs/miche-platform-architecture.md` in the htmlspec bundle — not paraphrased away:

**Stay on home + island:** "What's blocked?", "Run egghead on caffenagent gap", voice capture routed to memory, "Any sessions stale?"

**Open Focus:** read full htmlspec, diff a session, approve PR, FAB voice bank, long caffenagent grind.

## App registry as install manifest

Friends fork `interfaces/miche_app_registry.yaml`, add their app rows, set env URLs — no hard-coded operator Tailscale paths in island code. `MICHE_SINGLE_APP_DEV=1` may exist for local dev only with a loud UI banner; it is not the production default.

## Glossary

| Term | Meaning |
|------|---------|
| **miche_platform** | This repo — OS shell |
| **caffenagent** | Killer app — sessions, htmlspec, PRcrouch, Session Studio |
| **miche_harness** | Device/on-the-go layer in project-miche (PhonePanion, iPanion) |
| **Focus** | Full-app chrome for depth workflows |
| **Island** | Ambient docked voice+chat on home |

See also: [naming_canon.yaml](naming_canon.yaml).