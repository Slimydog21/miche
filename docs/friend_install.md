# Friend self-host install

**MPLAT-SPR-08** — run Miche Platform on your fork without operator secrets or corpus paths.

## Operator default (unchanged)

If you are the operator, do nothing: `MICHE_PROFILE` defaults to `operator_default`. Registry lives at `interfaces/miche_app_registry.yaml` with `install_profile: operator_default`. Secrets belong under `~/.miche/profiles/operator_default/secrets.env` — **never commit that file**.

## Friend install steps

1. **Fork** [Slimydog21/miche](https://github.com/Slimydog21/miche) and clone your fork locally.

2. **Copy the friend profile** (already in-repo): `interfaces/profiles/friend.yaml`. It allowlists only apps you should see (`moomba` in the stock template — replace with your app ids).

3. **Fork the registry** for your install:
   - Set `install_profile: friend` in `interfaces/miche_app_registry.yaml`.
   - Remove or disable `operator_only` apps (e.g. `caffenagent`) — friends must not point at the operator's Tailscale or corpus URLs.
   - Add your app rows with `base_url_env` pointing at *your* deployment.

4. **Create secrets file** (local only):
   ```bash
   mkdir -p ~/.miche/profiles/friend
   touch ~/.miche/profiles/friend/secrets.env
   chmod 600 ~/.miche/profiles/friend/secrets.env
   ```
   Put `KEY=value` lines for each `*_env` field in your registry (e.g. `MYAPP_PUBLIC_BASE_URL=https://myapp.example.test`). **Never commit secrets** — add `secrets.env` to `.gitignore` if you keep a copy elsewhere.

5. **Select the profile at runtime**:
   ```bash
   export MICHE_PROFILE=friend
   uv run python -m miche
   ```

6. **Verify isolation**: Home should not show operator-only Focus chips. Router audit lines in `logs/miche_router_dispatch.jsonl` (or `MICHE_ROUTER_DISPATCH_LOG`) include `profile_id: friend`. Dispatch to an operator app id must fail closed.

## Hard failures (by design)

| Condition | Result |
|-----------|--------|
| `MICHE_PROFILE=friend` but registry `install_profile: operator_default` | Startup error — profile mix-up |
| `secrets_path` outside `~/.miche/profiles/<profile_id>/` | Rejected — path traversal guard |
| Profile `apps[]` lists an id missing from registry | Rejected at load |

## What friends do not get

- Operator caffenagent / Session Studio / htmlspec corpus paths
- Billing or hosted SaaS auth (out of scope for SPR-08)

## Glossary

See [naming_canon.yaml](naming_canon.yaml) — **install_profile** is the named registry overlay for your tenant.