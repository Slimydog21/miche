# CI branch protection — MPLAT2-SPR-03

## Required check

- **platform / check** — must pass before merge to `main`

## Advisory (non-blocking)

- **platform / hardenx-advisory** — security scan; review logs on failure

## Operator setup (GitHub)

1. Settings → Branches → Add rule for `main`
2. Require status checks: `platform / check`
3. Do not require `hardenx-advisory` (continue-on-error)