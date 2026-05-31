"""
Singleton wrapper around JarvisVoice.
Lazy-loads on first use — models are large, don't load at import time.
"""
from __future__ import annotations

import sys
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Inject LuxTTS into path once, at module level (safe to repeat)
_LUX_PATH = Path(__file__).parent.parent.parent / "LuxTTS"
if str(_LUX_PATH) not in sys.path:
    sys.path.insert(0, str(_LUX_PATH))

_engine: Optional["JarvisVoice"] = None  # type: ignore[name-defined]


def get_voice_engine() -> "JarvisVoice":  # type: ignore[name-defined]
    """
    Returns the process-wide singleton JarvisVoice instance.
    First call loads both STT models and LuxTTS (~30s on first run, then cached).
    Subsequent calls are instant.
    """
    global _engine
    if _engine is None:
        from app.core.config import get_settings
        settings = get_settings()

        # Resolve device: honour VOICE_DEVICE env, fall back to GPU config
        device = settings.voice_device
        if device == "auto":
            try:
                import torch
                device = "cuda" if torch.cuda.is_available() else "cpu"
            except ImportError:
                device = "cpu"

        logger.info(f"Initialising JarvisVoice on device={device}")
        from app.voice.jarvis_voice import JarvisVoice
        _engine = JarvisVoice(device=device)

        # Load default voice references from env if configured
        if settings.voice_ref_en_path:
            try:
                _engine.set_default_voice(settings.voice_ref_en_path, lang="en")
                logger.info(f"EN voice ref loaded: {settings.voice_ref_en_path}")
            except Exception as exc:
                logger.warning(f"EN voice ref load failed: {exc}")

        if settings.voice_ref_mn_path:
            try:
                _engine.set_default_voice(settings.voice_ref_mn_path, lang="mn")
                logger.info(f"MN voice ref loaded: {settings.voice_ref_mn_path}")
            except Exception as exc:
                logger.warning(f"MN voice ref load failed: {exc}")

    return _engine
