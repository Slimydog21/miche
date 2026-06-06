"""Platform island API — MPLAT-SPR-05."""

from __future__ import annotations

from typing import Any

from fastapi import Body, File, Form, HTTPException, UploadFile
from fastapi.responses import JSONResponse

from ..island.router import new_utterance_id, route_utterance, router_mode
from ..island.thread import append_message, load_thread
from ..voice_ingest import ingest_voice, new_utterance_id as new_voice_id


def get_thread() -> dict[str, Any]:
    messages = load_thread()
    return {"ok": True, "messages": messages, "router_mode": router_mode()}


def post_utterance(body: dict[str, Any]) -> dict[str, Any]:
    utterance_id = str(body.get("utterance_id") or new_utterance_id())
    text = body.get("text")
    if not text or not str(text).strip():
        raise HTTPException(status_code=400, detail="text required")

    append_message(role="user", content=str(text).strip(), utterance_id=utterance_id)
    result = route_utterance(utterance_id=utterance_id, text=str(text).strip())
    append_message(
        role="assistant",
        content=result["reply_markdown"],
        utterance_id=utterance_id,
        inline_cards=result.get("inline_cards"),
    )
    return {"ok": True, **result}


def register_routes(app) -> None:
    @app.get("/api/platform/island/thread")
    def island_thread() -> JSONResponse:
        return JSONResponse(get_thread())

    @app.post("/api/platform/island/utterance")
    async def island_utterance(request_body: dict = Body(...)) -> JSONResponse:
        try:
            payload = post_utterance(request_body)
        except HTTPException:
            raise
        except Exception as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        return JSONResponse(payload)

    @app.post("/api/platform/island/voice")
    async def island_voice(
        utterance_id: str = Form(...),
        audio: UploadFile = File(...),
    ) -> JSONResponse:
        if not utterance_id.strip():
            utterance_id = new_voice_id()
        data = await audio.read()
        if not data:
            raise HTTPException(status_code=400, detail="empty audio payload")
        result = ingest_voice(
            utterance_id=utterance_id,
            audio_bytes=data,
            content_type=audio.content_type,
        )
        transcript = result.get("transcript")
        if result.get("asr_status") == "asr_skipped":
            user_line = f"[voice {result['audio_blob_id']}] {result['detail']}"
            append_message(role="user", content=user_line, utterance_id=utterance_id)
            route_result = route_utterance(
                utterance_id=utterance_id,
                text=user_line,
                audio_blob_id=result.get("audio_blob_id"),
            )
            append_message(
                role="assistant",
                content=route_result["reply_markdown"],
                utterance_id=utterance_id,
                inline_cards=route_result.get("inline_cards"),
            )
            result["user_line"] = user_line
            return JSONResponse({"ok": True, "voice": result, "route": route_result})

        if transcript:
            append_message(role="user", content=transcript, utterance_id=utterance_id)
            result["user_line"] = transcript
        elif result.get("asr_status") == "pending":
            pending_line = f"[voice {result['audio_blob_id']}] transcription pending"
            append_message(role="user", content=pending_line, utterance_id=utterance_id)
            append_message(
                role="assistant",
                content="Voice received — transcription pipeline deferred until SPR-06.",
                utterance_id=utterance_id,
            )
            result["user_line"] = pending_line
        return JSONResponse({"ok": True, "voice": result})