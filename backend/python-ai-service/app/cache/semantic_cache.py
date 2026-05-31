"""
Semantic Cache — two-layer response cache for Jarvis chat pipeline.

Layer 1 — Exact cache (Redis):
  Key: sha256(model + sorted messages JSON)
  Hit: 0 ms — no inference needed at all

Layer 2 — Semantic cache (Qdrant collection "semantic_cache"):
  Key: embedding of last user message
  Hit when cosine similarity >= threshold (default 0.95)
  Returns cached response from Redis by stored cache_key

Both layers are optional — any failure falls through gracefully.
TTL is configurable (default 24 h).

Usage:
    cache = SemanticCache.get_instance()
    hit = await cache.get(messages, model_id)
    if hit:
        return hit  # str response

    response = await llm_call(...)
    await cache.set(messages, model_id, response)
"""
from __future__ import annotations

import asyncio
import hashlib
import json
import os
import time
from typing import Any

from app.core.logging import get_logger

logger = get_logger(__name__)

_CACHE_COLLECTION = "semantic_cache"
_VECTOR_DIM = 384  # all-MiniLM-L6-v2


class SemanticCache:
    """Two-layer semantic cache: Redis (exact) + Qdrant (semantic)."""

    _instance: "SemanticCache | None" = None

    def __init__(
        self,
        redis_url: str,
        qdrant_host: str,
        qdrant_port: int,
        threshold: float = 0.95,
        ttl_seconds: int = 86400,
        enabled: bool = True,
    ):
        self._redis_url = redis_url
        self._qdrant_host = qdrant_host
        self._qdrant_port = qdrant_port
        self._threshold = threshold
        self._ttl = ttl_seconds
        self._enabled = enabled
        self._redis: Any = None
        self._qdrant: Any = None
        self._embedder: Any = None

    # ── Singleton ─────────────────────────────────────────────────────────────

    @classmethod
    def initialize(cls, **kwargs: Any) -> "SemanticCache":
        cls._instance = cls(**kwargs)
        return cls._instance

    @classmethod
    def get_instance(cls) -> "SemanticCache | None":
        return cls._instance

    # ── Boot ──────────────────────────────────────────────────────────────────

    async def boot(self) -> None:
        """Connect to Redis + Qdrant. Non-fatal — cache degrades silently."""
        if not self._enabled:
            logger.info("semantic_cache_disabled")
            return

        await asyncio.gather(
            self._init_redis(),
            self._init_qdrant(),
            return_exceptions=True,
        )
        logger.info(
            "semantic_cache_booted",
            redis=self._redis is not None,
            qdrant=self._qdrant is not None,
        )

    async def _init_redis(self) -> None:
        try:
            import redis.asyncio as aioredis  # type: ignore
            self._redis = await aioredis.from_url(
                self._redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2,
                socket_timeout=2,
            )
            await self._redis.ping()
            logger.info("semantic_cache_redis_connected")
        except Exception as exc:
            logger.warning("semantic_cache_redis_unavailable", reason=str(exc))
            self._redis = None

    async def _init_qdrant(self) -> None:
        try:
            from qdrant_client import QdrantClient
            from qdrant_client.models import Distance, VectorParams

            self._qdrant = QdrantClient(
                host=self._qdrant_host,
                port=self._qdrant_port,
                timeout=3,
            )
            # Ensure collection exists
            existing = {c.name for c in self._qdrant.get_collections().collections}
            if _CACHE_COLLECTION not in existing:
                self._qdrant.create_collection(
                    collection_name=_CACHE_COLLECTION,
                    vectors_config=VectorParams(size=_VECTOR_DIM, distance=Distance.COSINE),
                )
                logger.info("semantic_cache_collection_created")
        except Exception as exc:
            logger.warning("semantic_cache_qdrant_unavailable", reason=str(exc))
            self._qdrant = None

    def _get_embedder(self) -> Any:
        if self._embedder is not None:
            return self._embedder
        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")
        except Exception as exc:
            logger.debug("semantic_cache_embedder_unavailable", reason=str(exc))
        return self._embedder

    def _embed(self, text: str) -> list[float] | None:
        embedder = self._get_embedder()
        if embedder is None:
            return None
        try:
            vec = embedder.encode([text], normalize_embeddings=True)
            return vec[0].tolist()
        except Exception:
            return None

    # ── Cache key helpers ─────────────────────────────────────────────────────

    @staticmethod
    def _exact_key(messages: list[dict], model_id: str) -> str:
        payload = json.dumps({"model": model_id, "messages": messages}, sort_keys=True)
        return "jv:cache:" + hashlib.sha256(payload.encode()).hexdigest()

    @staticmethod
    def _last_user_msg(messages: list[dict]) -> str:
        for m in reversed(messages):
            if m.get("role") == "user":
                return m.get("content", "")
        return ""

    # ── Public API ────────────────────────────────────────────────────────────

    async def get(self, messages: list[dict], model_id: str) -> str | None:
        """Return cached response string or None."""
        if not self._enabled:
            return None

        # Layer 1: exact Redis match
        if self._redis is not None:
            try:
                key = self._exact_key(messages, model_id)
                hit = await asyncio.wait_for(self._redis.get(key), timeout=0.1)
                if hit:
                    logger.debug("cache_exact_hit", key=key[:16])
                    return hit
            except Exception as exc:
                logger.debug("cache_exact_miss", reason=str(exc))

        # Layer 2: semantic Qdrant match
        if self._qdrant is not None:
            user_msg = self._last_user_msg(messages)
            if user_msg:
                vec = await asyncio.get_event_loop().run_in_executor(
                    None, self._embed, user_msg
                )
                if vec is not None:
                    try:
                        hits = await asyncio.wait_for(
                            asyncio.get_event_loop().run_in_executor(
                                None,
                                lambda: self._qdrant.search(
                                    collection_name=_CACHE_COLLECTION,
                                    query_vector=vec,
                                    limit=1,
                                    score_threshold=self._threshold,
                                ),
                            ),
                            timeout=0.3,
                        )
                        if hits:
                            cache_key = hits[0].payload.get("cache_key", "")
                            if cache_key and self._redis is not None:
                                response = await asyncio.wait_for(
                                    self._redis.get(cache_key), timeout=0.1
                                )
                                if response:
                                    logger.debug(
                                        "cache_semantic_hit",
                                        score=round(hits[0].score, 3),
                                    )
                                    return response
                    except Exception as exc:
                        logger.debug("cache_semantic_miss", reason=str(exc))

        return None

    async def set(self, messages: list[dict], model_id: str, response: str) -> None:
        """Store response in both Redis (exact) and Qdrant (semantic). Fire-and-forget."""
        if not self._enabled or not response:
            return

        key = self._exact_key(messages, model_id)
        user_msg = self._last_user_msg(messages)

        async def _store() -> None:
            # Redis exact
            if self._redis is not None:
                try:
                    await self._redis.set(key, response, ex=self._ttl)
                except Exception as exc:
                    logger.debug("cache_redis_set_failed", reason=str(exc))

            # Qdrant semantic
            if self._qdrant is not None and user_msg:
                vec = await asyncio.get_event_loop().run_in_executor(
                    None, self._embed, user_msg
                )
                if vec is not None:
                    try:
                        from qdrant_client.models import PointStruct
                        import uuid as _uuid
                        point_id = str(_uuid.uuid4()).replace("-", "")[:16]
                        # Qdrant needs integer or UUID ids
                        await asyncio.get_event_loop().run_in_executor(
                            None,
                            lambda: self._qdrant.upsert(
                                collection_name=_CACHE_COLLECTION,
                                points=[
                                    PointStruct(
                                        id=abs(hash(key)) % (2**63),
                                        vector=vec,
                                        payload={
                                            "cache_key": key,
                                            "model": model_id,
                                            "stored_at": int(time.time()),
                                        },
                                    )
                                ],
                            ),
                        )
                    except Exception as exc:
                        logger.debug("cache_qdrant_set_failed", reason=str(exc))

        asyncio.ensure_future(_store())

    async def invalidate(self, messages: list[dict], model_id: str) -> None:
        """Explicitly remove a cached entry."""
        key = self._exact_key(messages, model_id)
        if self._redis is not None:
            try:
                await self._redis.delete(key)
            except Exception:
                pass
