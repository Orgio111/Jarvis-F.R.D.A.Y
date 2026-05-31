"""
SessionReplayStore — in-process + Redis-backed session replay storage.

Falls back to in-memory if Redis is unavailable.
"""
from __future__ import annotations

import json
import logging
import time
from typing import Any

from .models import ReplaySession, ReplayEvent, EventKind

logger = logging.getLogger(__name__)

_MAX_IN_MEMORY = 200   # keep last N sessions in memory
_REDIS_TTL     = 60 * 60 * 24 * 7  # 7 days


class SessionReplayStore:
    """Singleton store for all replay sessions."""

    _instance: "SessionReplayStore | None" = None

    def __init__(self) -> None:
        self._sessions: dict[str, ReplaySession] = {}
        self._order: list[str] = []            # insertion order
        self._redis = None
        self._try_connect_redis()

    # ── singleton ─────────────────────────────────────────────────────────────

    @classmethod
    def get(cls) -> "SessionReplayStore":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    # ── Redis ─────────────────────────────────────────────────────────────────

    def _try_connect_redis(self) -> None:
        try:
            import redis as redis_lib
            import os
            url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self._redis = redis_lib.from_url(url, decode_responses=True)
            self._redis.ping()
            logger.info("SessionReplayStore: Redis connected")
        except Exception:
            logger.warning("SessionReplayStore: Redis unavailable — using memory only")
            self._redis = None

    def _redis_key(self, session_id: str) -> str:
        return f"jarvis:replay:{session_id}"

    def _redis_index_key(self) -> str:
        return "jarvis:replay:_index"

    # ── CRUD ──────────────────────────────────────────────────────────────────

    def create_session(
        self,
        title: str = "Untitled",
        session_type: str = "chat",
        tags: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> ReplaySession:
        sess = ReplaySession(
            title=title,
            session_type=session_type,
            tags=tags or [],
            metadata=metadata or {},
        )
        self._store(sess)
        return sess

    def get_session(self, session_id: str) -> ReplaySession | None:
        # Memory first
        if session_id in self._sessions:
            return self._sessions[session_id]
        # Try Redis
        if self._redis:
            try:
                raw = self._redis.get(self._redis_key(session_id))
                if raw:
                    sess = ReplaySession.from_dict(json.loads(raw))
                    self._sessions[sess.session_id] = sess
                    return sess
            except Exception as exc:
                logger.warning("Redis get failed: %s", exc)
        return None

    def list_sessions(
        self,
        limit: int = 50,
        offset: int = 0,
        session_type: str | None = None,
        tag: str | None = None,
    ) -> list[dict]:
        sessions = list(reversed(self._order))   # newest first
        result = []
        for sid in sessions:
            sess = self._sessions.get(sid)
            if not sess:
                continue
            if session_type and sess.session_type != session_type:
                continue
            if tag and tag not in sess.tags:
                continue
            result.append(sess.to_dict(include_events=False))
        return result[offset: offset + limit]

    def append_event(self, session_id: str, event: ReplayEvent) -> bool:
        sess = self.get_session(session_id)
        if not sess:
            return False
        sess.add_event(event)
        self._persist(sess)
        return True

    def close_session(self, session_id: str) -> bool:
        sess = self.get_session(session_id)
        if not sess:
            return False
        sess.close()
        self._persist(sess)
        return True

    def delete_session(self, session_id: str) -> bool:
        if session_id in self._sessions:
            del self._sessions[session_id]
            if session_id in self._order:
                self._order.remove(session_id)
        if self._redis:
            try:
                self._redis.delete(self._redis_key(session_id))
                self._redis.lrem(self._redis_index_key(), 0, session_id)
            except Exception:
                pass
        return True

    # ── internals ─────────────────────────────────────────────────────────────

    def _store(self, sess: ReplaySession) -> None:
        self._sessions[sess.session_id] = sess
        if sess.session_id not in self._order:
            self._order.append(sess.session_id)
        # Evict oldest if over limit
        while len(self._order) > _MAX_IN_MEMORY:
            oldest = self._order.pop(0)
            self._sessions.pop(oldest, None)
        self._persist(sess)

    def _persist(self, sess: ReplaySession) -> None:
        if not self._redis:
            return
        try:
            self._redis.setex(
                self._redis_key(sess.session_id),
                _REDIS_TTL,
                json.dumps(sess.to_dict()),
            )
            # Update ordered index
            self._redis.lrem(self._redis_index_key(), 0, sess.session_id)
            self._redis.rpush(self._redis_index_key(), sess.session_id)
            self._redis.ltrim(self._redis_index_key(), -500, -1)
        except Exception as exc:
            logger.warning("Redis persist failed: %s", exc)
