from __future__ import annotations

import time

from fastapi import APIRouter, Request

from app.core.envelopes import success
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()

_start_time = time.time()

# Keep in sync with app/main.py FastAPI version (or override via env).
SERVICE_VERSION = "0.2.0"


@router.get("/health")
async def health(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    uptime_s = time.time() - _start_time
    return success(
        {
            "status": "pass",
            "uptime_seconds": round(uptime_s, 1),
            "service": "python-ai-service",
            "version": SERVICE_VERSION,
        },
        correlation_id,
    )
