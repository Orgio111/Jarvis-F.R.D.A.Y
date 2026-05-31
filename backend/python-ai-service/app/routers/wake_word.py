"""
Wake Word API router.

GET  /voice/wake/status    — detector status & config
POST /voice/wake/start     — start listening
POST /voice/wake/stop      — stop listening
PUT  /voice/wake/config    — update wake words / cooldown
"""
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from app.core.envelopes import success
from app.voice.wake_word import get_wake_word_detector

router = APIRouter(prefix="/voice/wake", tags=["wake_word"])

_sse_trigger_queue: list[float] = []   # timestamps of recent wake triggers


def _on_wake() -> None:
    import time
    _sse_trigger_queue.append(time.time())
    # Keep only last 20
    while len(_sse_trigger_queue) > 20:
        _sse_trigger_queue.pop(0)


class WakeConfigRequest(BaseModel):
    wake_words: list[str] | None = None
    cooldown_s: float | None = None


@router.get("/status")
async def wake_status():
    detector = get_wake_word_detector(callback=_on_wake)
    info = detector.get_info()
    info["recent_triggers"] = len(_sse_trigger_queue)
    return success(info)


@router.post("/start")
async def wake_start():
    detector = get_wake_word_detector(callback=_on_wake)
    if detector.status == "stopped":
        detector.start()
    return success({"status": detector.status})


@router.post("/stop")
async def wake_stop():
    detector = get_wake_word_detector(callback=_on_wake)
    detector.stop()
    return success({"status": detector.status})


@router.put("/config")
async def wake_config(body: WakeConfigRequest):
    detector = get_wake_word_detector(callback=_on_wake)
    was_running = detector.status == "listening"
    if was_running:
        detector.stop()
    if body.wake_words is not None:
        detector._wake_words = [w.lower() for w in body.wake_words]
    if body.cooldown_s is not None:
        detector._cooldown = body.cooldown_s
    if was_running:
        detector.start()
    return success(detector.get_info())
