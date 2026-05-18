from __future__ import annotations

import io
import uuid
from typing import Any

from fastapi import APIRouter, File, Request, UploadFile
from fastapi.responses import Response

from app.core.config import get_settings
from app.core.envelopes import error, success
from app.core.logging import get_logger
from app.gpu.detector import GPUDetector
from app.gpu.device_manager import DeviceManager

logger = get_logger(__name__)
router = APIRouter()


def _get_wr():
    """Lazy import to avoid circular deps at module load time."""
    from app.routers.gpu import get_workload_router
    return get_workload_router()


@router.post("/voice/stt")
async def speech_to_text(
    request: Request,
    audio: UploadFile = File(...),
) -> dict:
    """Transcribe an audio file to text using Faster Whisper (if installed)."""
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    if not settings.stt_enabled:
        return error("stt_disabled", "Speech-to-text is disabled", correlation_id=correlation_id)

    try:
        from faster_whisper import WhisperModel  # type: ignore[import]
    except ImportError:
        return error(
            "stt_unavailable",
            "Faster Whisper not installed — rebuild with the GPU image target.",
            correlation_id=correlation_id,
        )

    try:
        audio_bytes = await audio.read()
        audio_io = io.BytesIO(audio_bytes)

        wr = _get_wr()
        if wr is not None:
            # Use WorkloadRouter so the semaphore prevents concurrent OOM on GPU
            async with wr.acquire("stt") as device:
                compute_type = DeviceManager.resolve_compute_type("auto", device)
                model = WhisperModel(settings.stt_model_size, device=device, compute_type=compute_type)
                segments, info = model.transcribe(audio_io, beam_size=5)
                transcript = "".join(s.text for s in segments).strip()
        else:
            # Fallback before lifespan completes
            gpu_info = GPUDetector.get_info()
            device = DeviceManager.resolve(
                "auto", gpu_info.cuda_available and settings.stt_gpu_enabled, True
            )
            compute_type = DeviceManager.resolve_compute_type("auto", device)
            model = WhisperModel(settings.stt_model_size, device=device, compute_type=compute_type)
            segments, info = model.transcribe(audio_io, beam_size=5)
            transcript = "".join(s.text for s in segments).strip()

        return success(
            {
                "transcript": transcript,
                "language": info.language,
                "languageProbability": round(info.language_probability, 3),
                "duration": round(info.duration, 2),
            },
            correlation_id,
        )
    except Exception as exc:
        logger.error("stt_transcription_failed", error=str(exc))
        return error("stt_error", f"Transcription failed: {exc}", correlation_id=correlation_id)


@router.post("/voice/tts")
async def text_to_speech(request: Request) -> Any:
    """Synthesise speech from text. Returns audio/wav bytes."""
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    if not settings.tts_enabled:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content=error("tts_disabled", "Text-to-speech is disabled", correlation_id=correlation_id),
        )

    try:
        body = await request.json()
    except Exception:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Request body must be valid JSON", correlation_id=correlation_id),
        )

    text: str = body.get("text", "").strip()
    if not text:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "text is required", correlation_id=correlation_id),
        )

    try:
        import pyttsx3  # type: ignore[import]
        engine = pyttsx3.init()
        tmp_path = f"/tmp/tts_{uuid.uuid4().hex}.wav"
        engine.save_to_file(text, tmp_path)
        engine.runAndWait()
        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
        import os
        os.unlink(tmp_path)
        return Response(content=audio_bytes, media_type="audio/wav")
    except ImportError:
        pass
    except Exception as exc:
        logger.warning("pyttsx3_tts_failed", error=str(exc))

    # Fallback: return a 204 (no content) — TTS not available
    return Response(status_code=204)


@router.get("/voice/status")
async def voice_status(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()
    gpu_info = GPUDetector.get_info()

    wr = _get_wr()
    stt_device_mode = "unknown"
    if wr is not None:
        workloads = wr.get_workloads()
        stt_device_mode = workloads.get("stt", "cpu")

    stt_available = False
    try:
        import faster_whisper  # type: ignore[import] # noqa: F401
        stt_available = True
    except ImportError:
        pass

    tts_available = False
    try:
        import pyttsx3  # type: ignore[import] # noqa: F401
        tts_available = True
    except ImportError:
        pass

    return success(
        {
            "stt": {
                "enabled": settings.stt_enabled,
                "available": stt_available,
                "engine": settings.stt_engine,
                "device": stt_device_mode,
                "modelSize": settings.stt_model_size,
            },
            "tts": {
                "enabled": settings.tts_enabled,
                "available": tts_available,
                "engine": settings.tts_engine,
                "device": "cpu",
            },
        },
        correlation_id,
    )
