"""MPLAT-SPR-03 — action item JSON schema."""

from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

import jsonschema
import pytest

from miche.inbox.action import validate_action_item

_SCHEMA_PATH = Path(__file__).resolve().parent.parent / "schemas" / "miche_action_item.json"


@pytest.fixture
def schema():
    return json.loads(_SCHEMA_PATH.read_text())


def _sample(**overrides) -> dict:
    base = {
        "action_id": str(uuid.uuid4()),
        "title": "PR awaiting review",
        "severity": "blocking",
        "source_app": "caffenagent",
        "stale": False,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    base.update(overrides)
    return base


def test_schema_accepts_valid_item(schema):
    jsonschema.validate(instance=_sample(), schema=schema)


@pytest.mark.parametrize("severity", ["blocking", "soon", "nit"])
def test_severity_enum(severity, schema):
    jsonschema.validate(instance=_sample(severity=severity), schema=schema)


def test_invalid_severity_rejected(schema):
    with pytest.raises(jsonschema.ValidationError):
        jsonschema.validate(instance=_sample(severity="urgent"), schema=schema)


def test_validate_action_item_helper():
    validate_action_item(_sample())