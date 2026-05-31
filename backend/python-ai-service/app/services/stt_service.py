"""
faster-whisper STT Service — GPU-accelerated speech-to-text.

Uses the faster-whisper library (CTranslate2 backend) for fast inference:
  - GPU mode: runs on CUDA with float16 precision (RTX 4050)
  - CPU mode: runs with int8 quantization
  - Integrates with the WorkloadRouter for concurrency/backpressure
  - Supports language detection and custom model sizes
  - Singleton pattern (matching other services in the codebase)
"""

from __future__ import annotations

import os
import time
from typing import Any, Literal

from app.core.config import Settings, get_settings
from app.core.logging import get_logger
from app.gpu.detector import GPUDetector
from app.gpu.device_manager import DeviceManager

logger = get_logger(__name__)

# Optional import — faster-whisper may not be installed in the base image
try:
    from faster_whisper import WhisperModel
    _FASTER_WHISPER_AVAILABLE = True
except ImportError:
    WhisperModel = None  # type: ignore
    _FASTER_WHISPER_AVAILABLE = False


# Whisper model sizes mapped from config strings
_MODEL_SIZES = {
    "tiny": "tiny",
    "base": "base",
    "small": "small",
    "medium": "medium",
    "large": "large-v3",
    "large-v2": "large-v2",
    "large-v3": "large-v3",
    "distil-small": "distil-small.en",
    "distil-medium": "distil-medium.en",
    "distil-large": "distil-large-v3",
}


class STTService:
    """
    GPU-accelerated speech-to-text using faster-whisper.

    Features:
      - CUDA/CPU transparent selection based on settings & GPU availability
      - float16 on GPU, int8 on CPU (auto compute-type resolution)
      - Language detection + multi-language transcription
      - VAD filter for silence removal
      - Concurrency control via WorkloadRouter
      - Lazy model loading (model only loads on first transcribe)
    """

    _instance: STTService | None = None

    def __init__(self, settings: Settings):
        self._settings = settings
        self._model: Any = None
        self._model_size: str = settings.stt_model_size or "base"
        self._device: str = "cpu"
        self._compute_type: str = "int8"
        self._loaded = False
        self._load_time_ms: float = 0.0
        self._total_transcriptions: int = 0
        self._total_audio_seconds: float = 0.0

        # Resolve device and compute type
        device_str = settings.stt_device or "auto"
        resolved = DeviceManager.resolve(
            device_str,
            gpu_enabled=settings.stt_gpu_enabled and settings.gpu_enabled,
            allow_cpu_fallback=settings.gpu_allow_cpu_fallback,
        )
        # faster-whisper accepts 'cuda' (not 'cuda:0'), 'cpu', or 'auto'
        self._device = "cuda" if resolved.startswith("cuda") else resolved
        self._compute_type = DeviceManager.resolve_compute_type(
            settings.stt_compute_type or "auto",
            resolved,  # use the full device for compute type resolution
        )

        # Determine model name
        resolved_size = _MODEL_SIZES.get(
            self._model_size,
            self._model_size,
        )
        self._hf_model_id = resolved_size  # HuggingFace model ID or local path

        logger.info(
            "stt_service_configured",
            model_size=self._model_size,
            hf_model_id=self._hf_model_id,
            device=self._device,
            compute_type=self._compute_type,
            faster_whisper_available=_FASTER_WHISPER_AVAILABLE,
        )

    @classmethod
    def initialize(cls, settings: Settings) -> STTService:
        cls._instance = cls(settings)
        return cls._instance

    @classmethod
    def get(cls) -> STTService:
        if cls._instance is None:
            raise RuntimeError("STTService not initialized")
        return cls._instance

    @property
    def is_available(self) -> bool:
        return _FASTER_WHISPER_AVAILABLE

    @property
    def is_loaded(self) -> bool:
        return self._loaded

    # ── Model loading (lazy — first transcribe call) ──────────────────────────

    def _ensure_model(self) -> None:
        """Load the faster-whisper model if not already loaded."""
        if self._loaded:
            return
        if not _FASTER_WHISPER_AVAILABLE:
            raise RuntimeError(
                "faster-whisper is not installed. "
                "Install it with: pip install faster-whisper"
            )

        start = time.perf_counter()
        logger.info(
            "stt_loading_model",
            model_id=self._hf_model_id,
            device=self._device,
            compute_type=self._compute_type,
        )

        self._model = WhisperModel(
            self._hf_model_id,
            device=self._device,
            compute_type=self._compute_type,
            cpu_threads=4 if self._device == "cpu" else 0,
            num_workers=1,
            # Download root for caching downloaded models
            download_root=os.path.join(
                self._settings.data_dir, "models", "whisper"
            ),
        )
        self._loaded = True
        self._load_time_ms = (time.perf_counter() - start) * 1000
        logger.info(
            "stt_model_loaded",
            model_id=self._hf_model_id,
            load_time_ms=round(self._load_time_ms, 1),
        )

    # ── Core transcription ────────────────────────────────────────────────────

    async def transcribe(
        self,
        audio_path: str,
        language: str | None = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        word_timestamps: bool = False,
        initial_prompt: str | None = None,
    ) -> dict[str, Any]:
        """
        Transcribe an audio file using faster-whisper.

        Args:
            audio_path: Path to audio file (WAV, MP3, WebM, etc.)
            language: Language code ("mn", "en", None = auto-detect)
            beam_size: Beam search size (higher = better but slower)
            vad_filter: Apply VAD filter to remove silence
            word_timestamps: Include word-level timestamps
            initial_prompt: Optional prompt to guide transcription

        Returns:
            {
                "text": "...",
                "language": "mn" | "en" | ...,
                "languageProbability": 0.99,
                "duration": 12.5,
                "segments": [...],
                "device": "cuda:0" | "cpu",
                "computeType": "float16" | "int8",
            }
        """
        # Acquire concurrency slot from workload router
        try:
            from app.routers.gpu import get_workload_router
            wr = get_workload_router()
            if wr is not None:
                async with wr.acquire("stt") as device:
                    return await self._transcribe_inner(
                        audio_path, language, beam_size,
                        vad_filter, word_timestamps, initial_prompt,
                    )
            else:
                return await self._transcribe_inner(
                    audio_path, language, beam_size,
                    vad_filter, word_timestamps, initial_prompt,
                )
        except RuntimeError as exc:
            # Workload might be disabled — fall through to unguarded
            if "disabled" in str(exc):
                logger.warning("stt_workload_disabled_falling_back")
            return await self._transcribe_inner(
                audio_path, language, beam_size,
                vad_filter, word_timestamps, initial_prompt,
            )

    async def _transcribe_inner(
        self,
        audio_path: str,
        language: str | None = None,
        beam_size: int = 5,
        vad_filter: bool = True,
        word_timestamps: bool = False,
        initial_prompt: str | None = None,
    ) -> dict[str, Any]:
        """Inner transcription — runs in executor to avoid blocking the event loop."""
        self._ensure_model()

        # For auto-detection, ask faster-whisper to detect language
        detect_language = language is None

        loop = __import__("asyncio").get_event_loop()

        segments, info = await loop.run_in_executor(
            None,
            lambda: self._model.transcribe(
                audio_path,
                language=language,
                beam_size=beam_size,
                vad_filter=vad_filter,
                word_timestamps=word_timestamps,
                initial_prompt=initial_prompt,
                # Use VAD parameters tuned for conversational audio
                vad_parameters=dict(
                    threshold=0.5,
                    min_speech_duration_ms=250,
                    min_silence_duration_ms=100,
                ),
            ),
        )

        # Collect all segments
        all_segments = []
        full_text_parts = []

        for seg in segments:
            seg_dict = {
                "start": round(seg.start, 2),
                "end": round(seg.end, 2),
                "text": seg.text.strip(),
                "avgLogprob": round(seg.avg_logprob, 3),
                "noSpeechProb": round(seg.no_speech_prob, 3),
                "compressionRatio": round(seg.compression_ratio, 3),
            }
            if word_timestamps and seg.words:
                seg_dict["words"] = [
                    {
                        "word": w.word,
                        "start": round(w.start, 2),
                        "end": round(w.end, 2),
                        "probability": round(w.probability, 3),
                    }
                    for w in seg.words
                ]
            all_segments.append(seg_dict)
            full_text_parts.append(seg.text.strip())

        detected_lang = info.language if info else language or "unknown"
        lang_prob = round(info.language_probability, 3) if info else 1.0
        duration = round(info.duration, 2) if info else 0.0

        result = {
            "text": " ".join(full_text_parts),
            "language": detected_lang,
            "languageProbability": lang_prob,
            "duration": duration,
            "segments": all_segments,
            "segmentsCount": len(all_segments),
            "device": self._device,
            "computeType": self._compute_type,
            "modelSize": self._model_size,
        }

        self._total_transcriptions += 1
        self._total_audio_seconds += duration

        return result

    # ── Transcribe with file data (bytes) ─────────────────────────────────────

    async def transcribe_bytes(
        self,
        audio_bytes: bytes,
        suffix: str = ".wav",
        language: str | None = None,
        **kwargs,
    ) -> dict[str, Any]:
        """
        Transcribe audio from bytes. Writes to a temp file internally.
        """
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            try:
                tmp.write(audio_bytes)
                tmp.flush()
                tmp_path = tmp.name
            finally:
                tmp.close()

        try:
            result = await self.transcribe(tmp_path, language=language, **kwargs)
        finally:
            try:
                os.unlink(tmp_path)
            except Exception:
                pass

        return result

    # ── Status ────────────────────────────────────────────────────────────────

    def get_status(self) -> dict[str, Any]:
        """Return STT engine status."""
        gpu_info = GPUDetector.get_info()
        return {
            "available": _FASTER_WHISPER_AVAILABLE,
            "loaded": self._loaded,
            "engine": "faster-whisper",
            "modelSize": self._model_size,
            "hfModelId": self._hf_model_id,
            "device": self._device,
            "computeType": self._compute_type,
            "loadTimeMs": round(self._load_time_ms, 1) if self._loaded else None,
            "gpu": {
                "cudaAvailable": gpu_info.cuda_available,
                "deviceCount": gpu_info.device_count,
                "devices": gpu_info.devices,
            },
            "stats": {
                "totalTranscriptions": self._total_transcriptions,
                "totalAudioSeconds": round(self._total_audio_seconds, 1),
            },
            "config": {
                "enabled": self._settings.stt_enabled,
                "gpuEnabled": self._settings.stt_gpu_enabled,
                "vadFilter": True,
                "beamSize": 5,
            },
        }
