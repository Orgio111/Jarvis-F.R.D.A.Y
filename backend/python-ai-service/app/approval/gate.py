"""
Approval Gate — blocks dangerous agent actions until a human approves/rejects.

Flow:
  1. Agent calls ApprovalGate.request(action, details) → gets request_id
  2. Gate suspends the coroutine via asyncio.Event
  3. Human approves or rejects via the REST API (/approval/{id}/respond)
  4. Gate resumes and returns True (approved) or raises ApprovalDeniedError

Risk levels:
  LOW    — log only, auto-approve
  MEDIUM — notify but auto-approve after timeout
  HIGH   — block until human responds
  CRITICAL — block forever until explicit response
"""
from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

logger = logging.getLogger(__name__)

_DEFAULT_TIMEOUT_S = 300   # 5 min timeout for MEDIUM gates
_MAX_PENDING = 100


class RiskLevel(str, Enum):
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


class ApprovalStatus(str, Enum):
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    TIMED_OUT = "timed_out"
    AUTO_APPROVED = "auto_approved"


class ApprovalDeniedError(Exception):
    """Raised when a gate is rejected."""
    def __init__(self, request_id: str, reason: str = ""):
        super().__init__(f"Action denied [{request_id}]: {reason}")
        self.request_id = request_id
        self.reason = reason


@dataclass
class ApprovalRequest:
    request_id:  str         = field(default_factory=lambda: f"apr_{uuid4().hex[:10]}")
    action:      str         = ""
    description: str         = ""
    risk_level:  RiskLevel   = RiskLevel.HIGH
    details:     dict[str, Any] = field(default_factory=dict)
    status:      ApprovalStatus = ApprovalStatus.PENDING
    created_at:  float       = field(default_factory=time.time)
    resolved_at: float | None = None
    resolved_by: str | None   = None   # "user" | "timeout" | "auto"
    reject_reason: str        = ""

    # Internal: asyncio event for blocking
    _event: asyncio.Event = field(default_factory=asyncio.Event, repr=False, compare=False)

    def to_dict(self) -> dict:
        return {
            "request_id":   self.request_id,
            "action":       self.action,
            "description":  self.description,
            "risk_level":   self.risk_level.value,
            "details":      self.details,
            "status":       self.status.value,
            "created_at":   self.created_at,
            "resolved_at":  self.resolved_at,
            "resolved_by":  self.resolved_by,
            "reject_reason": self.reject_reason,
        }


class ApprovalGate:
    """Singleton gate manager."""

    _instance: "ApprovalGate | None" = None
    _pending:  dict[str, ApprovalRequest]
    _history:  list[ApprovalRequest]

    def __init__(self) -> None:
        self._pending = {}
        self._history = []

    @classmethod
    def get(cls) -> "ApprovalGate":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Public API ────────────────────────────────────────────────────────────

    async def request(
        self,
        action: str,
        description: str = "",
        risk_level: RiskLevel = RiskLevel.HIGH,
        details: dict[str, Any] | None = None,
        timeout_s: float | None = None,
    ) -> bool:
        """
        Submit an approval request and wait for human decision.
        Returns True if approved, raises ApprovalDeniedError if rejected.
        """
        req = ApprovalRequest(
            action=action,
            description=description,
            risk_level=risk_level,
            details=details or {},
        )

        # LOW — just log, auto-approve
        if risk_level == RiskLevel.LOW:
            req.status = ApprovalStatus.AUTO_APPROVED
            req.resolved_by = "auto"
            req.resolved_at = time.time()
            self._history.append(req)
            logger.info("Gate AUTO-APPROVED [low risk]: %s", action)
            return True

        # Evict oldest if queue full
        if len(self._pending) >= _MAX_PENDING:
            oldest = next(iter(self._pending))
            self._reject_internal(oldest, "queue_overflow")

        self._pending[req.request_id] = req
        logger.warning("Gate PENDING [%s]: %s — %s", risk_level.value, action, req.request_id)

        # MEDIUM — auto-approve after timeout
        effective_timeout = timeout_s
        if risk_level == RiskLevel.MEDIUM and effective_timeout is None:
            effective_timeout = _DEFAULT_TIMEOUT_S

        try:
            if effective_timeout:
                await asyncio.wait_for(req._event.wait(), timeout=effective_timeout)
            else:
                await req._event.wait()
        except asyncio.TimeoutError:
            req.status = ApprovalStatus.TIMED_OUT
            req.resolved_at = time.time()
            req.resolved_by = "timeout"
            self._pending.pop(req.request_id, None)
            self._history.append(req)
            if risk_level == RiskLevel.MEDIUM:
                logger.info("Gate TIMED-OUT (auto-approve for medium): %s", action)
                return True
            raise ApprovalDeniedError(req.request_id, "timed out")

        # Check final status
        self._pending.pop(req.request_id, None)
        self._history.append(req)

        if req.status == ApprovalStatus.APPROVED:
            return True
        raise ApprovalDeniedError(req.request_id, req.reject_reason)

    def respond(
        self,
        request_id: str,
        approved: bool,
        reason: str = "",
        resolved_by: str = "user",
    ) -> bool:
        req = self._pending.get(request_id)
        if not req:
            return False
        req.status = ApprovalStatus.APPROVED if approved else ApprovalStatus.REJECTED
        req.reject_reason = reason
        req.resolved_at = time.time()
        req.resolved_by = resolved_by
        req._event.set()
        logger.info(
            "Gate %s by %s: %s — %s",
            req.status.value.upper(), resolved_by, req.action, request_id,
        )
        return True

    def list_pending(self) -> list[dict]:
        return [r.to_dict() for r in self._pending.values()]

    def get_request(self, request_id: str) -> ApprovalRequest | None:
        return self._pending.get(request_id) or next(
            (r for r in self._history if r.request_id == request_id), None
        )

    def history(self, limit: int = 50) -> list[dict]:
        return [r.to_dict() for r in list(reversed(self._history))[:limit]]

    # ── internals ─────────────────────────────────────────────────────────────

    def _reject_internal(self, request_id: str, reason: str) -> None:
        req = self._pending.pop(request_id, None)
        if req:
            req.status = ApprovalStatus.REJECTED
            req.reject_reason = reason
            req.resolved_at = time.time()
            req.resolved_by = "system"
            req._event.set()
            self._history.append(req)
