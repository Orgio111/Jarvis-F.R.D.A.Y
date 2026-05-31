"""
STT (Speech-to-Text) API routes — GPU-accelerated faster-whisper.

Endpoints:
  POST /stt/transcribe  — Upload audio file, get transcription text
  GET  /stt/status      — STT engine status (device, model, stats)
"""

from __future__ import annotations

import os
import tempfile
from typing import Any

from fastapi import APIRouter, File, Form, Query, Request, UploadFile

from app.core.envelopes import error, success
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter(prefix="/stt", tags=["stt"])


def _get_service():
    """Get the STTService singleton."""
    try:
        from app.services.stt_service import STTService
        return STTService.get()
    except RuntimeError as exc:
        from fastapi import HTTPException
        raise HTTPException(status_code=503, detail=str(exc))


# ─── Supported audio formats ──────────────────────────────────────────────────

_SUPPORTED_EXTENSIONS = {".wav", ".mp3", ".webm", ".ogg", ".flac", ".m4a", ".opus"}
_MAX_AUDIO_SIZE_MB = 50
_MAX_AUDIO_SIZE_BYTES = _MAX_AUDIO_SIZE_MB * 1024 * 1024


# ─── POST /stt/transcribe ─────────────────────────────────────────────────────

@router.post("/transcribe")
async def transcribe_audio(
    request: Request,
    audio: UploadFile = File(..., description="Audio file (WAV, MP3, WebM, etc.)"),
    language: str = Form(
        default="",
        description="Language code: 'mn', 'en', or empty for auto-detect",
    ),
    beam_size: int = Form(default=5, ge=1, le=20),
    vad_filter: bool = Form(default=True, description="Voice Activity Detection filter"),
    word_timestamps: bool = Form(default=False, description="Include word-level timestamps"),
    initial_prompt: str = Form(default="", description="Optional prompt to guide transcription"),
) -> dict[str, Any]:
    """
    Transcribe an audio file to text using faster-whisper on GPU.

    Supports WAV, MP3, WebM, OGG, FLAC, M4A, and Opus formats.
    Max file size: 50 MB.

    Returns the transcribed text, detected language, duration, and segments.
    """
    correlation_id = request.headers.get("x-correlation-id")

    # Check if STT is enabled
    from app.core.config import get_settings
    settings = get_settings()
    if not settings.stt_enabled:
        return error(
            "stt_disabled",
            "Speech-to-text is disabled by configuration",
            correlation_id=correlation_id,
        )

    # Check service availability
    try:
        svc = _get_service()
    except Exception as exc:
        return error(
            "stt_unavailable",
            f"STT service not available: {exc}",
            correlation_id=correlation_id,
        )

    if not svc.is_available:
        return error(
            "stt_not_installed",
            "faster-whisper is not installed in this environment. "
            "Use the GPU Docker image (docker-compose.gpu.yml).",
            correlation_id=correlation_id,
        )

    # Validate file extension
    ext = os.path.splitext(audio.filename or "audio.wav")[1].lower()
    if ext not in _SUPPORTED_EXTENSIONS:
        return error(
            "unsupported_format",
            f"Unsupported audio format '{ext}'. "
            f"Supported: {', '.join(sorted(_SUPPORTED_EXTENSIONS))}",
            correlation_id=correlation_id,
        )

    # Read audio bytes
    try:
        audio_bytes = await audio.read()
    except Exception as exc:
        return error(
            "audio_read_error",
            f"Failed to read audio file: {exc}",
            correlation_id=correlation_id,
        )

    # Size check
    if len(audio_bytes) > _MAX_AUDIO_SIZE_BYTES:
        return error(
            "audio_too_large",
            f"Audio file too large ({len(audio_bytes) / 1024 / 1024:.1f} MB). "
            f"Max: {_MAX_AUDIO_SIZE_MB} MB",
            correlation_id=correlation_id,
        )

    if len(audio_bytes) == 0:
        return error(
            "audio_empty",
            "Audio file is empty",
            correlation_id=correlation_id,
        )

    # Resolve language
    lang = language.strip() or None  # None = auto-detect

    try:
        result = await svc.transcribe_bytes(
            audio_bytes,
            suffix=ext,
            language=lang,
            beam_size=beam_size,
            vad_filter=vad_filter,
            word_timestamps=word_timestamps,
            initial_prompt=initial_prompt.strip() or None,
        )
        return success(result, correlation_id)

    except Exception as exc:
        logger.error("stt_transcribe_failed", error=str(exc))
        return error(
            "stt_error",
            f"Transcription failed: {exc}",
            correlation_id=correlation_id,
        )


# ─── GET /stt/status ──────────────────────────────────────────────────────────

@router.get("/status")
async def stt_status(request: Request) -> dict[str, Any]:
    """Return STT engine status (device, model, stats)."""
    correlation_id = request.headers.get("x-correlation-id")

    try:
        svc = _get_service()
        status = svc.get_status()
        return success(status, correlation_id)
    except Exception as exc:
        # Return a basic status even if service is not initialized
        from app.core.config import get_settings
        from app.gpu.detector import GPUDetector

        settings = get_settings()
        gpu_info = GPUDetector.get_info()

        return success(
            {
                "available": False,
                "loaded": False,
                "engine": "faster-whisper",
                "device": "unknown",
                "config": {
                    "enabled": settings.stt_enabled,
                    "gpuEnabled": settings.stt_gpu_enabled,
                },
                "gpu": {
                    "cudaAvailable": gpu_info.cuda_available,
                    "deviceCount": gpu_info.device_count,
                },
                "error": str(exc),
            },
            correlation_id,
        )
