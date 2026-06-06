#!/usr/bin/env bash
# MPLAT-SPR-10 / MPLAT2-SPR-06 — Platform capstone: island triage → audit bundle + rules_v0 smoke.
# Usage: bash harness/miche_platform_capstone_drill.sh --cassette
set -euo pipefail

ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

if [[ "${1:-}" != "--cassette" ]]; then
  echo "miche_platform_capstone_drill: only --cassette supported in v1" >&2
  exit 2
fi

export MICHE_ROUTER_FIXTURE=cassette
export MICHE_ISLAND_ROUTER_FIXTURE=cassette
export PYTHONPATH="${ROOT}:${PYTHONPATH:-}"

CAPSTONE_RUN_ID="$(uv run python - <<'PY'
import uuid
print(uuid.uuid4())
PY
)"

TMP_LOG="$(mktemp -d)"
export MICHE_ROUTER_DISPATCH_LOG="${TMP_LOG}/router.jsonl"
export MICHE_ISLAND_UTTERANCE_LOG="${TMP_LOG}/island.jsonl"
export MICHE_PERSONA_RENDER_LOG="${TMP_LOG}/persona.jsonl"
export CAPSTONE_RUN_ID

echo "miche_platform_capstone_drill: capstone_run_id=${CAPSTONE_RUN_ID}"
echo "miche_platform_capstone_drill: step 1 — home shell + persona (no network)"

uv run python - <<'PY'
import json
from pathlib import Path

from fastapi.testclient import TestClient

from miche.web import create_app

client = TestClient(create_app())

home = client.get("/")
assert home.status_code == 200, home.text
assert "miche-island-mount" in home.text
assert "miche-home-mascot" in home.text

persona = client.get("/api/miche/persona", params={"context": "island"})
assert persona.status_code == 200
body = persona.json()
assert body["persona_id"] == "engine"
assert body["sprite_url"].startswith("/static/")
print(f"  persona engine animation={body['animation_key']}")
PY

echo "miche_platform_capstone_drill: step 2 — island utterance cassette triage"
uv run python - <<'PY'
import json
from pathlib import Path

from fastapi.testclient import TestClient

from miche.web import create_app

fixture_dir = Path("harness/fixtures/platform_capstone")
utterance = (fixture_dir / "utterance_stale_sessions.txt").read_text().strip()
expected = json.loads((fixture_dir / "expected_evidence.json").read_text())

client = TestClient(create_app())
resp = client.post(
    "/api/platform/island/utterance",
    json={"text": utterance},
)
assert resp.status_code == 200, resp.text
body = resp.json()
assert body.get("inline_cards"), "expected inline card from router"
card = body["inline_cards"][0]
assert card["type"] == expected["expected_card_type"]
assert body.get("router_decision_id")
print(f"  utterance routed app={body.get('inline_cards')[0].get('source_app_id')} cards={len(body['inline_cards'])}")
PY

echo "miche_platform_capstone_drill: step 2b — rules_v0 smoke (no cassette env)"
uv run python - <<'PY'
import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from miche.web import create_app

for key in ("MICHE_ROUTER_FIXTURE", "MICHE_ISLAND_ROUTER_FIXTURE"):
    os.environ.pop(key, None)

tmpdir = Path(os.environ["MICHE_ROUTER_DISPATCH_LOG"]).parent
rules_log = tmpdir / "rules_router.jsonl"
os.environ["MICHE_ROUTER_DISPATCH_LOG"] = str(rules_log)

client = TestClient(create_app())
resp = client.post(
    "/api/miche/router/dispatch",
    json={"utterance_id": "rules-1", "text": "list sessions"},
)
assert resp.status_code == 200, resp.text
row = json.loads(rules_log.read_text().strip().splitlines()[-1])
assert row["router_mode"] == "rules_v0", row

blocked_log = tmpdir / "blocked_router.jsonl"
os.environ["MICHE_ROUTER_DISPATCH_LOG"] = str(blocked_log)
resp2 = client.post(
    "/api/miche/router/dispatch",
    json={"utterance_id": "rules-2", "text": "what is blocked right now"},
)
assert resp2.status_code == 200
row2 = json.loads(blocked_log.read_text().strip().splitlines()[-1])
assert row2["router_mode"] == "inbox_fallback", row2
print(f"  rules_v0 ok; inbox_fallback ok")
PY

echo "miche_platform_capstone_drill: step 3 — inbox + optional focus contract"
uv run python - <<'PY'
import json
from pathlib import Path

from fastapi.testclient import TestClient

from miche.web import create_app

client = TestClient(create_app())

action = client.get("/api/platform/inbox/actions")
assert action.status_code == 200
action_body = action.json()
assert "items" in action_body

info = client.get("/api/platform/inbox/information")
assert info.status_code == 200

focus = client.get("/focus/caffenagent", follow_redirects=False)
assert focus.status_code in {302, 400, 200}, focus.status_code
print(f"  action_items={len(action_body.get('items') or [])} focus_status={focus.status_code}")
PY

echo "miche_platform_capstone_drill: step 4 — audit JSONL evidence"
uv run python - <<PY
import json
import os
from pathlib import Path

router_log = Path(os.environ["MICHE_ROUTER_DISPATCH_LOG"])
island_log = Path(os.environ["MICHE_ISLAND_UTTERANCE_LOG"])
persona_log = Path(os.environ["MICHE_PERSONA_RENDER_LOG"])

for label, path in [("router", router_log), ("island", island_log), ("persona", persona_log)]:
    assert path.is_file(), f"missing {label} audit log"
    lines = [json.loads(l) for l in path.read_text().splitlines() if l.strip()]
    assert lines, f"empty {label} audit"
    print(f"  {label}_lines={len(lines)}")

router_row = json.loads(router_log.read_text().strip().splitlines()[-1])
assert router_row.get("profile_id")
assert router_row.get("router_decision_id")

island_row = json.loads(island_log.read_text().strip().splitlines()[-1])
assert island_row.get("profile_id")

signoff = Path("docs/decisions/island-craft-signoff.md")
craft_sha = signoff.read_text(encoding="utf-8")[:64] if signoff.is_file() else None
handoff = {
    "capstone_run_id": os.environ.get("CAPSTONE_RUN_ID", "unknown"),
    "mode": "cassette",
    "check_platform_version": "scripts/check_platform.sh",
    "craft_signoff_present": signoff.is_file(),
    "router_evidence": router_row,
    "island_evidence": island_row,
}
out = Path("harness/fixtures/platform_capstone/last_capstone_handoff.json")
out.write_text(json.dumps(handoff, indent=2) + "\n")
print(f"  handoff archived {out}")
PY

echo "miche_platform_capstone_drill: step 5 — capstone contract tests (narrow; check_platform runs full suite)"
unset MICHE_ROUTER_DISPATCH_LOG MICHE_ISLAND_UTTERANCE_LOG MICHE_PERSONA_RENDER_LOG
uv run pytest -q --tb=line tests/test_platform_capstone.py

echo "miche_platform_capstone_drill: --cassette OK capstone_run_id=${CAPSTONE_RUN_ID}"