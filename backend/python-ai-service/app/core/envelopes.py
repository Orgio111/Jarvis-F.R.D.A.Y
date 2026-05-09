from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Generic, TypeVar
from uuid import uuid4

from pydantic import BaseModel, Field

T = TypeVar("T")


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


class ApiSuccess(BaseModel, Generic[T]):
    ok: bool = True
    data: T
    correlationId: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=_now_iso)


class ApiErrorDetail(BaseModel):
    code: str
    message: str
    details: dict[str, Any] | None = None


class ApiError(BaseModel):
    ok: bool = False
    error: ApiErrorDetail
    correlationId: str = Field(default_factory=lambda: str(uuid4()))
    timestamp: str = Field(default_factory=_now_iso)


class BackendEvent(BaseModel, Generic[T]):
    id: str = Field(default_factory=lambda: f"evt_{uuid4()}")
    type: str
    version: str = "1.0"
    timestamp: str = Field(default_factory=_now_iso)
    correlationId: str = Field(default_factory=lambda: str(uuid4()))
    requestId: str | None = None
    sessionId: str | None = None
    source: str = "backend"
    payload: T


def success(data: Any, correlation_id: str | None = None) -> dict:
    return {
        "ok": True,
        "data": data,
        "correlationId": correlation_id or str(uuid4()),
        "timestamp": _now_iso(),
    }


def error(
    code: str,
    message: str,
    details: dict | None = None,
    correlation_id: str | None = None,
) -> dict:
    return {
        "ok": False,
        "error": {
            "code": code,
            "message": message,
            "details": details,
        },
        "correlationId": correlation_id or str(uuid4()),
        "timestamp": _now_iso(),
    }


def new_event(
    event_type: str,
    payload: Any,
    correlation_id: str | None = None,
    request_id: str | None = None,
    session_id: str | None = None,
) -> dict:
    return {
        "id": f"evt_{uuid4()}",
        "type": event_type,
        "version": "1.0",
        "timestamp": _now_iso(),
        "correlationId": correlation_id or str(uuid4()),
        "requestId": request_id,
        "sessionId": session_id,
        "source": "backend",
        "payload": payload,
    }
