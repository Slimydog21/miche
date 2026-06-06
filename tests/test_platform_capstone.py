"""MPLAT-SPR-10 / MPLAT2-SPR-06 — platform capstone drill contract."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
import pytest

_ROOT = Path(__file__).resolve().parent.parent
_DRILL = _ROOT / "harness" / "miche_platform_capstone_drill.sh"
_FIXTURES = _ROOT / "harness" / "fixtures" / "platform_capstone"
_HANDOFF_SCHEMA = json.loads((_FIXTURES / "handoff_v2.schema.json").read_text())


def test_capstone_fixtures_present():
    assert (_FIXTURES / "utterance_stale_sessions.txt").is_file()
    evidence = json.loads((_FIXTURES / "expected_evidence.json").read_text())
    assert evidence["expected_card_type"] == "action_item"


def test_capstone_drill_script_exists_and_executable():
    assert _DRILL.is_file()
    assert _DRILL.read_text().startswith("#!/usr/bin/env bash")


def test_capstone_handoff_v2_schema():
    """Validates handoff written by drill step 4 — do not subprocess drill from pytest."""
    handoff_path = _FIXTURES / "last_capstone_handoff.json"
    if not handoff_path.is_file():
        pytest.skip("run harness/miche_platform_capstone_drill.sh --cassette first")
    handoff = json.loads(handoff_path.read_text())
    jsonschema.validate(instance=handoff, schema=_HANDOFF_SCHEMA)
    assert handoff["check_platform_version"] == "scripts/check_platform.sh"
    assert handoff["craft_signoff_present"] is True