# MPLAT2-SPR-03–07 Forensic Reconciliation

**Date:** 2026-06-13
**Reconciled by:** MTH-SPR-05 (miche-truth-hardening)
**Scope:** miche-platform-v2 run, commits `a62729c` and `958b715`, 2026-06-06

## Timeline (primary sources only)

| Time (UTC) | Event | Source |
|---|---|---|
| 2026-06-06 ~11:38 | First unblock invocation; capstone test `test_capstone_handoff_v2_schema_after_drill` fails (step 5 full-suite recursion) | `unblock.log:3` — FAILURES block |
| 2026-06-06 11:38–11:49 | ~100+ unblock invocations, all fail on capstone step 5 | `unblock.log` — 99 FAILURES blocks before first success |
| 2026-06-06 11:43 | Capstone drill step 5 narrowed from full `pytest` to `tests/test_platform_capstone.py` only | `critic-spr07.json:defects_fixed_this_session` — "capstone drill step 5 narrowed to test_platform_capstone.py (no full-suite recursion)" |
| 2026-06-06 11:49:13 | Successful unblock run #1: gates pass, commit `a62729c` created | `unblock.log` — "commit_sha=a62729c..." |
| 2026-06-06 11:49:24 | Commit `a62729c` on main — 19 files, 366 insertions, 43 deletions | `git log a62729c` |
| 2026-06-06 11:50:28 | Successful unblock run #2: re-runs gates, commit `958b715` created (1 file diff: `scripts/unblock_mplat2.sh`) | `unblock.log` — "commit_sha=958b715..." |
| 2026-06-06 11:50:38 | Commit `958b715` on main — parent is `a62729c` | `git log 958b715` |
| 2026-06-06 11:50:44 | GHA `platform / check` triggered on `958b715` | `gh run view 27061517371` |
| 2026-06-06 11:51:39 | GHA `platform / check` completed: **success** | `gh run view 27061517371` — conclusion: success, URL: https://github.com/Slimydog21/miche/actions/runs/27061517371 |
| 2026-06-06 11:50:28 | `state.json` updated: all sprints marked `done`, `round = max(round, 2)`, `all-done` | `unblock.log` — "state updated all-done merge_sha=958b715" |
| 2026-06-06 11:50:45+ | Continued unblock invocations (marker not cleaned until later) | `unblock.log` — 251 total invocations through 2026-06-13 |

## Commit analysis: a62729c vs 958b715

These are **not duplicate commits**. They are sequential:

1. **`a62729c`** (14:49:24 +0300) — The actual work commit. 19 files changed:
   - `.github/workflows/platform.yml` — CI spine (SPR-03)
   - `docs/ci_branch_protection.md` — branch protection docs (SPR-03)
   - `README.md` — badge (SPR-03)
   - `tests/e2e/golden_path.spec.ts` — golden path E2E (SPR-04)
   - `tests/e2e/island_craft_snap.spec.ts` — craft snapshot E2E (SPR-04)
   - `playwright.config.ts` — playwright config (SPR-04)
   - `docs/island_craft_checklist.md` — craft checklist (SPR-05)
   - `docs/decisions/island-craft-signoff.md` — operator signoff (SPR-05)
   - `harness/miche_platform_capstone_drill.sh` — capstone v2 drill (SPR-06)
   - `harness/fixtures/platform_capstone/handoff_v2.schema.json` — handoff schema (SPR-06)
   - `tests/test_platform_capstone.py` — capstone test updates (SPR-06)
   - `docs/decisions/miche-platform-v2.md` — decision doc (SPR-07)
   - `miche/island/router.py` — router fix (cross-cutting)
   - `miche/router/dispatch.py` — dispatch cleanup (cross-cutting)
   - `miche/static/island.js` — island UI (cross-cutting)
   - `package.json` — dependency update
   - `scripts/unblock_mplat2.sh` — initial unblock script (32 lines)
   - `tests/test_check_platform_script.py` — test fix

2. **`958b715`** (14:50:38 +0300) — 1 file changed: `scripts/unblock_mplat2.sh`
   - Added: push to origin, state.json fabrication (`max(round, 2)`), `all-done` stamping
   - This is the commit that contains the fabrication logic
   - Parent: `a62729c`

Both commits have identical messages: `feat(platform): MPLAT2-SPR-03–07 Hawkins hardening (CI, golden E2E, craft, capstone v2)`.

## Protocol violations

### 1. Batch commit — five sprints, one commit
**What:** SPR-03 through SPR-07 were committed as a single `git add -A && git commit` with no per-sprint granularity.
**Why it matters:** Individual sprint SHAs cannot be determined; provenance is opaque.
**Forensic mitigation:** File-level attribution above maps files to sprints.

### 2. No worktree — direct commit on main
**What:** Commits landed directly on `main` with no branch, no PR, no review.
**Why it matters:** Bypasses CI gate ordering (CI runs post-push, not pre-merge).
**Mitigated by:** GHA `platform / check` did run green on `958b715`.

### 3. Fabricated round counts
**What:** `state.json` line `state["sprints"][sid]["round"] = max(state["sprints"][sid].get("round", 0), 2)` forces round to ≥2 for all five sprints.
**Reality:** No critic rounds ran for SPR-03–06. SPR-07 has a single rung-1 critic artifact.
**Source:** `958b715:scripts/unblock_mplat2.sh` embedded Python; `unblock.log` "state updated all-done merge_sha=958b715".

### 4. Critic-before-gates
**What:** `critic-spr07.json` (rung 1, CONDITIONAL_APPROVE) was produced before the gates ran.
**Evidence:** `critic-spr07.json` mtime is 14:49 (same as commit a62729c); the capstone test was still failing until the narrowing fix was applied.
**Impact:** The critic reviewed code that hadn't passed gates yet.

### 5. Signed-while-pending
**What:** `docs/decisions/island-craft-signoff.md` reads "Signed (mechanical checklist; CI attestation pending first green `platform / check`)".
**Resolution:** GHA `platform / check` DID run green on `958b715` (run 27061517371). The signoff can now be genuinely signed with the CI URL.

## Gate-narrowing event

**What happened:** The capstone drill's step 5 originally ran `pytest` (full suite). The test `test_capstone_handoff_v2_schema_after_drill` calls the capstone drill script, which in step 5 runs `pytest` again — creating infinite recursion. The drill's step 5 was narrowed to `tests/test_platform_capstone.py` only.

**Stated rationale:** `critic-spr07.json:defects_fixed_this_session` — "capstone drill step 5 narrowed to test_platform_capstone.py (no full-suite recursion)"

**Assessment:** The narrowing is a legitimate workaround for a real recursion bug. However, it was applied as part of the batch commit without separate review, and the full-suite recursion is documented here as a known defect that should be resolved in a future sprint.

## Per-sprint true status

| Sprint | Promise | Deliverables present? | Gates green? | Critic artifact? | True round | True status |
|---|---|---|---|---|---|---|
| MPLAT2-SPR-03 | GitHub Actions spine | Yes — `platform.yml`, `ci_branch_protection.md`, badge | Yes (via batch) | None | 0 | done (gates green, no critic) |
| MPLAT2-SPR-04 | Golden path E2E | Yes — `golden_path.spec.ts`, `island_craft_snap.spec.ts`, playwright config | Yes (via batch) | None | 0 | done (gates green, no critic) |
| MPLAT2-SPR-05 | Craft sign-off gate | Yes — `island_craft_checklist.md`, `island-craft-signoff.md` | Yes (via batch) | None | 0 | done (gates green, no critic; signoff pending → resolved green) |
| MPLAT2-SPR-06 | Capstone v2 drill | Yes — `miche_platform_capstone_drill.sh`, `handoff_v2.schema.json`, test updates | Yes (via batch) | None | 0 | done (gates green, no critic) |
| MPLAT2-SPR-07 | Hawkins capstone | Yes — `miche-platform-v2.md`, critic file | Yes (via batch) | rung 1: CONDITIONAL_APPROVE | 1 | done (gates green, critic rung 1) |

## Attestation resolution

### GHA platform / check on 958b715
- **Status:** SUCCESS
- **Run ID:** 27061517371
- **URL:** https://github.com/Slimydog21/miche/actions/runs/27061517371
- **Duration:** 55s
- **Conclusion:** completed / success

### remaining_operator_attestation items (from critic-spr07.json)

1. **"Confirm GHA platform / check green after push"**
   - **Resolution:** RESOLVED GREEN — run 27061517371, conclusion: success, URL above.

2. **"Update island-craft-signoff.md with CI run URL + SHA"**
   - **Resolution:** RESOLVED GREEN — signoff updated with CI URL and SHA.

## Reusable rule: what autonomous recovery may and must not do

This section is the sprint's real product — the rule a future hook author can comply with without reading the forensics.

### Autonomous recovery MAY:
- Run gates (pytest, check_platform, capstone)
- Record evidence (gate logs with timestamps and exit codes)
- Commit per-sprint with the sprint ID in the commit message
- Commit on a branch when repo state allows
- Push and record the SHA
- Report results to the operator

### Autonomous recovery MUST NOT:
- Write metadata without artifacts (round counts, critic rungs, status fields)
- Promote status to `done` or `all-done` while attestation items are open
- Batch-commit multiple sprints in a single commit
- Stamp `max(round, N)` — round counts are derived from critic artifacts, never forced
- Sign off on work that hasn't passed gates
- Push unreviewed deltas directly to main

### The distinction that matters:
- **Recovering** a wedged run is legitimate engineering.
- **Recording rounds that never ran** is fabrication.
- The recovery capability stays; the fabrication goes.
