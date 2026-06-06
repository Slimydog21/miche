"""Island conversation thread persistence — MPLAT-SPR-05."""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


def _default_thread_path() -> Path:
    override = os.environ.get("MICHE_ISLAND_THREAD_PATH", "").strip()
    if override:
        return Path(override)
    return Path.home() / ".miche" / "island_thread.jsonl"


_THREAD_LOG = _default_thread_path()
_MAX_MESSAGES = 50


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def thread_path() -> Path:
    return _THREAD_LOG


def append_message(
    *,
    role: str,
    content: str,
    utterance_id: str | None = None,
    inline_cards: list[dict[str, Any]] | None = None,
    path: Path | None = None,
) -> dict[str, Any]:
    row = {
        "message_id": utterance_id or _iso_now(),
        "role": role,
        "content": content,
        "utterance_id": utterance_id,
        "inline_cards": inline_cards or [],
        "created_at": _iso_now(),
    }
    log = path or _THREAD_LOG
    log.parent.mkdir(parents=True, exist_ok=True)
    with log.open("a") as f:
        f.write(json.dumps(row) + "\n")
    return row


def load_thread(*, limit: int = _MAX_MESSAGES, path: Path | None = None) -> list[dict[str, Any]]:
    log = path or _THREAD_LOG
    if not log.is_file():
        return []
    rows: list[dict[str, Any]] = []
    with log.open() as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            rows.append(json.loads(line))
    return rows[-limit:]