"""
Async HTTP client that talks to the JARVIS Go Gateway (or directly to the
Python AI service when the gateway is not running).

All methods return plain dicts or raise on non-2xx responses.
Streaming helpers yield raw text lines from SSE endpoints.
"""
from __future__ import annotations

import json
import os
from collections.abc import AsyncGenerator
from typing import Any

import httpx

_DEFAULT_GATEWAY = os.getenv("JARVIS_URL", "http://localhost:8000")
_TIMEOUT = httpx.Timeout(60.0, connect=5.0)


class JarvisClient:
    def __init__(self, base_url: str = _DEFAULT_GATEWAY, api_key: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    # ─── Chat ─────────────────────────────────────────────────────────────────

    async def chat_stream(
        self,
        messages: list[dict],
        model: str = "",
        session_id: str = "",
        user_id: str = "default",
    ) -> AsyncGenerator[dict[str, Any], None]:
        """Stream SSE tokens from /chat/completions."""
        headers = {**self._headers}
        if session_id:
            headers["x-session-id"] = session_id
        if user_id:
            headers["x-user-id"] = user_id

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                json={"messages": messages, "model": model, "stream": True},
                headers=headers,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        yield json.loads(raw)
                    except json.JSONDecodeError:
                        pass

    async def chat(
        self,
        messages: list[dict],
        model: str = "",
        session_id: str = "",
        user_id: str = "default",
    ) -> str:
        """Non-streaming chat — returns assembled content string."""
        headers = {**self._headers}
        if session_id:
            headers["x-session-id"] = session_id
        if user_id:
            headers["x-user-id"] = user_id

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json={"messages": messages, "model": model, "stream": False},
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("content", "")

    # ─── Memory ───────────────────────────────────────────────────────────────

    async def memory_search(self, query: str, top_k: int = 5) -> list[dict]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self.base_url}/memory/search",
                json={"query": query, "topK": top_k},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json().get("data", {}).get("results", [])

    async def memory_store(self, content: str, metadata: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self.base_url}/memory/store",
                json={"content": content, "metadata": metadata or {}},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def memory_status(self) -> dict:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{self.base_url}/memory/status", headers=self._headers)
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def memory_recent(self, limit: int = 10) -> list[dict]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(
                f"{self.base_url}/memory/recent",
                params={"limit": limit},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json().get("data", {}).get("entries", [])

    # ─── Skills ───────────────────────────────────────────────────────────────

    async def skills_list(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{self.base_url}/skills", headers=self._headers)
            resp.raise_for_status()
            return resp.json().get("data", {}).get("skills", [])

    async def skill_create(self, name: str, description: str, category: str = "general") -> dict:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self.base_url}/skills",
                json={"name": name, "description": description, "category": category},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    async def skill_run(self, skill_id: str, params: dict | None = None) -> dict:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self.base_url}/skills/{skill_id}/execute",
                json={"params": params or {}},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json().get("data", {})

    # ─── Agent ────────────────────────────────────────────────────────────────

    async def agent_run_stream(self, goal: str, max_iterations: int = 3) -> AsyncGenerator[dict, None]:
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/agent/run",
                json={"goal": goal, "stream": True, "maxIterations": max_iterations},
                headers=self._headers,
            ) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    raw = line[5:].strip()
                    if raw == "[DONE]":
                        break
                    try:
                        yield json.loads(raw)
                    except json.JSONDecodeError:
                        pass

    # ─── Models & Providers ───────────────────────────────────────────────────

    async def models_list(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{self.base_url}/models", headers=self._headers)
            resp.raise_for_status()
            return resp.json().get("data", {}).get("models", [])

    async def providers_status(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{self.base_url}/providers/status", headers=self._headers)
            resp.raise_for_status()
            return resp.json().get("data", {}).get("providers", [])

    async def health(self) -> dict:
        async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
            resp = await client.get(f"{self.base_url}/health", headers=self._headers)
            resp.raise_for_status()
            return resp.json()

    # ─── Scheduler ────────────────────────────────────────────────────────────

    async def scheduler_tasks(self) -> list[dict]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{self.base_url}/scheduler/tasks", headers=self._headers)
            resp.raise_for_status()
            return resp.json().get("data", {}).get("tasks", [])
