"""MPLAT-SPR-10 — platform capstone drill contract."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_DRILL = _ROOT / "harness" / "miche_platform_capstone_drill.sh"
_FIXTURES = _ROOT / "harness" / "fixtures" / "platform_capstone"


def test_capstone_fixtures_present():
    assert (_FIXTURES / "utterance_stale_sessions.txt").is_file()
    evidence = json.loads((_FIXTURES / "expected_evidence.json").read_text())
    assert evidence["expected_card_type"] == "action_item"


def test_capstone_drill_script_exists_and_executable():
    assert _DRILL.is_file()
    assert _DRILL.stat().st_mode & 0o111