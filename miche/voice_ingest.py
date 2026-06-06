"""Island voice ingest — MPLAT-SPR-05."""

from __future__ import annotations

import os
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

_VOICE_DIR = Path.home() / ".miche" / "island_voice"


def _iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def has_asr_key() -> bool:
    return bool(os.environ.get("MICHE_ASR_API_KEY", "").strip())


def ingest_voice(
    *,
    utterance_id: str,
    audio_bytes: bytes,
    content_type: str | None = None,
) -> dict[str, Any]:
    _VOICE_DIR.mkdir(parents=True, exist_ok=True)
    ext = "webm"
    if content_type and "ogg" in content_type:
        ext = "ogg"
    blob_id = f"{utterance_id}.{ext}"
    blob_path = _VOICE_DIR / blob_id
    blob_path.write_bytes(audio_bytes)

    if not has_asr_key():
        return {
            "ok": True,
            "utterance_id": utterance_id,
            "audio_blob_id": blob_id,
            "transcript": None,
            "asr_status": "asr_skipped",
            "detail": "MICHE_ASR_API_KEY unset — honest dev stub, not a fake transcript.",
            "created_at": _iso_now(),
        }

    return {
        "ok": True,
        "utterance_id": utterance_id,
        "audio_blob_id": blob_id,
        "transcript": None,
        "asr_status": "pending",
        "detail": "ASR key present; transcription pipeline deferred to SPR-06.",
        "created_at": _iso_now(),
    }


def new_utterance_id() -> str:
    return str(uuid.uuid4())