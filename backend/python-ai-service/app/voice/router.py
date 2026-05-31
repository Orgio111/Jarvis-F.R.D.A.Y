"""
Voice API router — MN+EN bilingual STT/TTS.
Replaces the old faster-whisper / Coqui / pyttsx3 router entirely.

Endpoints:
  POST /voice/stt         — audio file → transcript (lang: mn|en|auto)
  POST /voice/tts         — text → WAV audio bytes (lang: mn|en)
  POST /voice/set-ref     — upload reference WAV for voice clone
  GET  /voice/status      — engine status
"""
from __future__ import annotations

import io
import os
import uuid
import asyncio
import logging
import tempfile
from typing import Any, Literal

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse, Response

from app.core.config import get_settings
from app.core.envelopes import error, success

logger = logging.getLogger(__name__)
router = APIRouter()


# ─── helpers ──────────────────────────────────────────────────────────────────

def _get_engine():
    from app.voice.engine import get_voice_engine
    return get_voice_engine()


def _resolve_lang_stt(lang: str) -> Literal["mn", "en", "auto"]:
    if lang in ("mn", "en", "auto"):
        return lang  # type: ignore[return-value]
    return "auto"


def _resolve_lang_tts(lang: str) -> Literal["mn", "en"]:
    return "mn" if lang == "mn" else "en"


# ─── POST /voice/stt ──────────────────────────────────────────────────────────

@router.post("/voice/stt")
async def speech_to_text(
    request: Request,
    audio: UploadFile = File(...),
    lang: str = Form(default="auto"),
) -> dict:
    """
    Transcribe an audio file (WAV/WebM/MP3) to text.

    Form fields:
      audio  — audio file (required)
      lang   — "mn" | "en" | "auto" (default: auto)
    """
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    if not settings.stt_enabled:
        return error("stt_disabled", "Speech-to-text is disabled", correlation_id=correlation_id)

    lang_resolved = _resolve_lang_stt(lang)

    try:
        audio_bytes = await audio.read()

        # Write to a temp file — transformers pipeline needs a file path or numpy array
        suffix = ".wav" if audio.filename and audio.filename.endswith(".wav") else ".webm"
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            tmp.write(audio_bytes)
            tmp.flush()
            tmp_path = tmp.name
        finally:
            tmp.close()

        loop = asyncio.get_running_loop()
        engine = _get_engine()

        transcript: str = await loop.run_in_executor(
            None,
            engine.transcribe,
            tmp_path,
            lang_resolved,
        )

        # Detect actual language from script
        cyrillic = sum(1 for c in transcript if "\u0400" <= c <= "\u04FF")
        detected_lang = "mn" if cyrillic > len(transcript) * 0.3 else "en"

        return success(
            {
                "transcript": transcript,
                "language": detected_lang,
                "requestedLang": lang_resolved,
            },
            correlation_id,
        )

    except Exception as exc:
        logger.error(f"stt_failed: {exc}")
        return error("stt_error", f"Transcription failed: {exc}", correlation_id=correlation_id)

    finally:
        try:
            os.unlink(tmp_path)
        except Exception:
            pass


# ─── POST /voice/tts ──────────────────────────────────────────────────────────

@router.post("/voice/tts")
async def text_to_speech(request: Request) -> Any:
    """
    Synthesise speech from text. Returns audio/wav (48 kHz).

    JSON body:
      text        — required
      lang        — "mn" | "en" (default: "en")
      speed       — float, default 1.0
      num_steps   — int, default 4
      t_shift     — float, default 0.7
      voice_ref   — server-side path to reference WAV (optional; use /voice/set-ref to upload)
    """
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    if not settings.tts_enabled:
        return JSONResponse(
            status_code=503,
            content=error("tts_disabled", "Text-to-speech is disabled", correlation_id=correlation_id),
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Request body must be valid JSON", correlation_id=correlation_id),
        )

    text: str = body.get("text", "").strip()
    if not text:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "text is required", correlation_id=correlation_id),
        )

    lang = _resolve_lang_tts(body.get("lang", "en"))
    speed: float = float(body.get("speed", 1.0))
    num_steps: int = int(body.get("num_steps", 4))
    t_shift: float = float(body.get("t_shift", 0.7))
    voice_ref: str | None = body.get("voice_ref") or None

    try:
        engine = _get_engine()
        loop = asyncio.get_running_loop()

        wav = await loop.run_in_executor(
            None,
            lambda: engine.speak(
                text,
                lang=lang,
                voice_ref=voice_ref,
                speed=speed,
                num_steps=num_steps,
                t_shift=t_shift,
            ),
        )

        # Write to bytes buffer
        import soundfile as sf
        buf = io.BytesIO()
        sf.write(buf, wav, 48000, format="WAV")
        buf.seek(0)
        audio_bytes = buf.read()

        return Response(content=audio_bytes, media_type="audio/wav")

    except ValueError as exc:
        # e.g. no voice reference configured
        logger.warning(f"tts_config_error: {exc}")
        return JSONResponse(
            status_code=400,
            content=error("tts_config_error", str(exc), correlation_id=correlation_id),
        )
    except Exception as exc:
        logger.error(f"tts_failed: {exc}")
        return JSONResponse(
            status_code=500,
            content=error("tts_error", f"TTS failed: {exc}", correlation_id=correlation_id),
        )


# ─── POST /voice/set-ref ──────────────────────────────────────────────────────

@router.post("/voice/set-ref")
async def set_voice_reference(
    request: Request,
    audio: UploadFile = File(...),
    lang: str = Form(default="en"),
) -> dict:
    """
    Upload a reference WAV (≥3s) to set the default voice for TTS.

    Form fields:
      audio  — WAV file
      lang   — "mn" | "en" (default: "en")
    """
    correlation_id = request.headers.get("x-correlation-id")
    lang_resolved: Literal["mn", "en"] = "mn" if lang == "mn" else "en"

    try:
        audio_bytes = await audio.read()

        # Persist to data dir so it survives restarts
        data_dir = get_settings().data_dir
        ref_dir = os.path.join(data_dir, "voice_refs")
        os.makedirs(ref_dir, exist_ok=True)
        ref_path = os.path.join(ref_dir, f"default_{lang_resolved}.wav")

        with open(ref_path, "wb") as f:
            f.write(audio_bytes)

        # Update live engine
        loop = asyncio.get_running_loop()
        engine = _get_engine()
        await loop.run_in_executor(
            None,
            engine.set_default_voice,
            ref_path,
            lang_resolved,
        )

        return success(
            {
                "lang": lang_resolved,
                "path": ref_path,
                "sizeBytes": len(audio_bytes),
            },
            correlation_id,
        )

    except Exception as exc:
        logger.error(f"set_ref_failed: {exc}")
        return error("set_ref_error", f"Failed to set voice reference: {exc}", correlation_id=correlation_id)


# ─── GET /voice/status ────────────────────────────────────────────────────────

@router.get("/voice/status")
async def voice_status(request: Request) -> dict:
    """Returns current STT/TTS engine status."""
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    try:
        import torch
        cuda_available = torch.cuda.is_available()
    except ImportError:
        cuda_available = False

    device = settings.voice_device
    if device == "auto":
        device = "cuda" if cuda_available else "cpu"

    # Check if engine is already loaded (don't trigger load just for status)
    from app.voice import engine as _engine_mod
    engine_loaded = _engine_mod._engine is not None

    # Check voice refs
    data_dir = settings.data_dir
    ref_dir = os.path.join(data_dir, "voice_refs")
    en_ref = os.path.exists(os.path.join(ref_dir, "default_en.wav")) or bool(settings.voice_ref_en_path)
    mn_ref = os.path.exists(os.path.join(ref_dir, "default_mn.wav")) or bool(settings.voice_ref_mn_path)

    return success(
        {
            "stt": {
                "enabled": settings.stt_enabled,
                "available": True,
                "engine": "jarvis-voice-mn-en",
                "device": device,
                "models": {
                    "mn": "bayartsogt/whisper-large-v2-mn-13",
                    "en": "openai/whisper-large-v2",
                },
                "loaded": engine_loaded,
            },
            "tts": {
                "enabled": settings.tts_enabled,
                "available": True,
                "engine": "LuxTTS",
                "device": device,
                "model": "YatharthS/LuxTTS",
                "sampleRate": 48000,
                "loaded": engine_loaded,
                "voiceRefs": {
                    "en": en_ref,
                    "mn": mn_ref,
                },
            },
        },
        correlation_id,
    )
