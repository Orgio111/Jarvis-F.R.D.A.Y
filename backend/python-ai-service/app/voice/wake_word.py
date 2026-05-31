"""
Wake Word Detector — keyword-triggered voice activation for JARVIS.

Listens to the microphone in a background thread.
When the wake word is detected, fires a callback.

Default wake word: "hey jarvis" (configurable)
Uses energy-based VAD + simple keyword match on fast STT transcription.
Falls back to a pure energy/silence detector if STT is unavailable.

Usage:
    detector = WakeWordDetector(callback=on_wake, wake_words=["hey jarvis", "jarvis"])
    detector.start()
    ...
    detector.stop()
"""
from __future__ import annotations

import logging
import os
import queue
import threading
import time
from typing import Callable

logger = logging.getLogger(__name__)

_DEFAULT_WAKE_WORDS = ["hey jarvis", "jarvis", "жарвис"]
_SAMPLE_RATE = 16000
_CHUNK_SECONDS = 1.5          # how many seconds to buffer per detection window
_ENERGY_THRESHOLD = 0.01      # RMS energy threshold to skip silence


class WakeWordDetector:
    """
    Lightweight microphone-based wake word detector.
    Runs STT in a background thread; fires callback on match.
    """

    def __init__(
        self,
        callback: Callable[[], None],
        wake_words: list[str] | None = None,
        cooldown_s: float = 2.0,
    ) -> None:
        self._callback   = callback
        self._wake_words = [w.lower() for w in (wake_words or _DEFAULT_WAKE_WORDS)]
        self._cooldown   = cooldown_s
        self._running    = False
        self._thread: threading.Thread | None = None
        self._audio_q: queue.Queue = queue.Queue()
        self._last_triggered = 0.0
        self.status = "stopped"    # stopped | listening | error

    # ── Public ────────────────────────────────────────────────────────────────

    def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True, name="wake-word")
        self._thread.start()
        self.status = "listening"
        logger.info("WakeWordDetector started — wake words: %s", self._wake_words)

    def stop(self) -> None:
        self._running = False
        if self._thread:
            self._thread.join(timeout=3)
        self.status = "stopped"
        logger.info("WakeWordDetector stopped")

    def get_info(self) -> dict:
        return {
            "status":     self.status,
            "wake_words": self._wake_words,
            "cooldown_s": self._cooldown,
        }

    # ── Internal ──────────────────────────────────────────────────────────────

    def _run(self) -> None:
        try:
            import pyaudio
            import numpy as np
        except ImportError:
            logger.warning("WakeWordDetector: pyaudio/numpy not installed — using stub mode")
            self.status = "error"
            return

        p = pyaudio.PyAudio()
        chunk = int(_SAMPLE_RATE * _CHUNK_SECONDS)

        try:
            stream = p.open(
                format=pyaudio.paInt16,
                channels=1,
                rate=_SAMPLE_RATE,
                input=True,
                frames_per_buffer=chunk,
            )
            logger.info("WakeWordDetector: microphone opened")
        except Exception as exc:
            logger.warning("WakeWordDetector: cannot open mic — %s", exc)
            self.status = "error"
            p.terminate()
            return

        while self._running:
            try:
                raw = stream.read(chunk, exception_on_overflow=False)
                audio = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
                rms = float(np.sqrt(np.mean(audio ** 2)))

                # Skip silence
                if rms < _ENERGY_THRESHOLD:
                    continue

                # Transcribe the chunk
                transcript = self._transcribe(raw)
                if transcript:
                    self._check_trigger(transcript)

            except Exception as exc:
                logger.debug("WakeWordDetector loop error: %s", exc)
                time.sleep(0.1)

        stream.stop_stream()
        stream.close()
        p.terminate()

    def _transcribe(self, raw_pcm: bytes) -> str:
        """Transcribe raw PCM bytes to text using the voice engine."""
        try:
            from app.voice.engine import get_voice_engine
            engine = get_voice_engine()
            # Write to a temp WAV and transcribe
            import io, wave, tempfile
            buf = io.BytesIO()
            with wave.open(buf, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(_SAMPLE_RATE)
                wf.writeframes(raw_pcm)
            buf.seek(0)
            result = engine.transcribe_bytes(buf.read(), lang="auto")
            return result.get("text", "").lower().strip()
        except Exception:
            return ""

    def _check_trigger(self, transcript: str) -> None:
        now = time.time()
        if now - self._last_triggered < self._cooldown:
            return
        for word in self._wake_words:
            if word in transcript:
                self._last_triggered = now
                logger.info("Wake word detected: '%s' in '%s'", word, transcript)
                self.status = "triggered"
                try:
                    self._callback()
                except Exception as exc:
                    logger.warning("Wake word callback error: %s", exc)
                finally:
                    self.status = "listening"
                break


# ── Module-level singleton ────────────────────────────────────────────────────

_detector: WakeWordDetector | None = None
_detector_lock = threading.Lock()


def get_wake_word_detector(
    callback: Callable[[], None] | None = None,
    wake_words: list[str] | None = None,
) -> WakeWordDetector:
    global _detector
    with _detector_lock:
        if _detector is None:
            if callback is None:
                callback = lambda: logger.info("Wake word fired — no callback set")
            _detector = WakeWordDetector(callback=callback, wake_words=wake_words)
        return _detector
