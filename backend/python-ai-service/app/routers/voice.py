from __future__ import annotations

import asyncio
import io
import os
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

# Module-level WhisperModel cache — keyed by "<model_size>:<device>:<compute_type>"
# Loading the model once per process avoids ~5 s cold-start on every STT request.
_whisper_cache: dict[str, "WhisperModel"] = {}  # type: ignore[name-defined]


def _get_whisper_model(model_size: str, device: str, compute_type: str) -> "WhisperModel":  # type: ignore[name-defined]
    from faster_whisper import WhisperModel  # type: ignore[import]
    key = f"{model_size}:{device}:{compute_type}"
    if key not in _whisper_cache:
        logger.info("whisper_model_loading", key=key)
        _whisper_cache[key] = WhisperModel(model_size, device=device, compute_type=compute_type)
        logger.info("whisper_model_loaded", key=key)
    return _whisper_cache[key]


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
        import faster_whisper  # type: ignore[import]  # noqa: F401
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
                model = _get_whisper_model(settings.stt_model_size, device, compute_type)
                segments, info = model.transcribe(audio_io, beam_size=5)
                transcript = "".join(s.text for s in segments).strip()
        else:
            # Fallback before lifespan completes
            gpu_info = GPUDetector.get_info()
            device = DeviceManager.resolve(
                "auto", gpu_info.cuda_available and settings.stt_gpu_enabled, True
            )
            compute_type = DeviceManager.resolve_compute_type("auto", device)
            model = _get_whisper_model(settings.stt_model_size, device, compute_type)
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


def _run_coqui(model_name: str, text: str, language: str, speed: float, device: str, out_path: str) -> None:
    """Blocking Coqui TTS synthesis — call from an executor thread."""
    from TTS.api import TTS as CoquiTTS  # type: ignore[import]
    tts = CoquiTTS(model_name=model_name, progress_bar=False).to(device)
    tts.tts_to_file(
        text=text,
        file_path=out_path,
        language=language if tts.is_multi_lingual else None,
        speed=speed,
    )


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

    voice_id: str = body.get("voice", "")
    language: str = body.get("language", "en")
    speed: float = float(body.get("speed", 1.0))

    gpu_info = GPUDetector.get_info()
    use_gpu = gpu_info.cuda_available and settings.tts_gpu_enabled != "false"
    tts_device = "cuda" if use_gpu else "cpu"
    model_name = voice_id if voice_id else "tts_models/en/ljspeech/tacotron2-DDC"
    wr = _get_wr()

    # ── Try Coqui TTS (GPU-capable) ──────────────────────────────────────────
    try:
        from TTS.api import TTS as CoquiTTS  # type: ignore[import]  # noqa: F401

        tmp_path = f"/tmp/tts_{uuid.uuid4().hex}.wav"
        loop = asyncio.get_running_loop()

        if wr is not None:
            async with wr.acquire("tts"):
                await loop.run_in_executor(
                    None, _run_coqui, model_name, text, language, speed, tts_device, tmp_path
                )
        else:
            await loop.run_in_executor(
                None, _run_coqui, model_name, text, language, speed, tts_device, tmp_path
            )

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
        os.unlink(tmp_path)
        return Response(content=audio_bytes, media_type="audio/wav")

    except ImportError:
        pass  # Coqui TTS not installed — fall back
    except Exception as exc:
        logger.warning("coqui_tts_failed", error=str(exc))

    # ── Fallback: pyttsx3 (CPU-only) ─────────────────────────────────────────
    try:
        import pyttsx3  # type: ignore[import]

        tmp_path = f"/tmp/tts_{uuid.uuid4().hex}.wav"

        def _run_pyttsx3() -> None:
            engine = pyttsx3.init()
            if speed != 1.0:
                rate = engine.getProperty("rate")
                engine.setProperty("rate", int(rate * speed))
            engine.save_to_file(text, tmp_path)
            engine.runAndWait()

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _run_pyttsx3)

        with open(tmp_path, "rb") as f:
            audio_bytes = f.read()
        os.unlink(tmp_path)
        return Response(content=audio_bytes, media_type="audio/wav")

    except ImportError:
        pass
    except Exception as exc:
        logger.warning("pyttsx3_tts_failed", error=str(exc))

    # No TTS engine available
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
    tts_engine_name = "none"
    tts_device = "cpu"

    try:
        from TTS.api import TTS as CoquiTTS  # type: ignore[import] # noqa: F401
        tts_available = True
        tts_engine_name = "coqui"
        gpu_info = GPUDetector.get_info()
        tts_device = "cuda" if gpu_info.cuda_available and settings.tts_gpu_enabled != "false" else "cpu"
    except ImportError:
        try:
            import pyttsx3  # type: ignore[import] # noqa: F401
            tts_available = True
            tts_engine_name = "pyttsx3"
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
                "engine": tts_engine_name,
                "device": tts_device,
                "gpuEnabled": settings.tts_gpu_enabled,
            },
        },
        correlation_id,
    )
