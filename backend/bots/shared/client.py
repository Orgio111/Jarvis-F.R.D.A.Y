"""
Shared async HTTP client used by both the Telegram and Discord bots.
All bots talk to the Go Gateway; this client is identical to the CLI
client but slimmer (no streaming helpers for bots — polling instead).
"""
from __future__ import annotations

import json
import os
from typing import Any

import httpx

_GATEWAY = os.getenv("JARVIS_URL", "http://localhost:8000")
_TIMEOUT = httpx.Timeout(60.0, connect=5.0)


class BotClient:
    def __init__(self, base_url: str = _GATEWAY, api_key: str = "") -> None:
        self.base_url = base_url.rstrip("/")
        self._headers: dict[str, str] = {"Content-Type": "application/json"}
        if api_key:
            self._headers["Authorization"] = f"Bearer {api_key}"

    async def chat(
        self,
        user_text: str,
        session_id: str = "",
        user_id: str = "default",
        model: str = "",
    ) -> str:
        headers = {**self._headers}
        if session_id:
            headers["x-session-id"] = session_id
        if user_id:
            headers["x-user-id"] = user_id

        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                json={
                    "messages": [{"role": "user", "content": user_text}],
                    "model": model,
                    "stream": False,
                },
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            return data.get("data", {}).get("content", "")

    async def run_agent(self, goal: str, user_id: str = "default") -> str:
        """Run agent loop and return the final answer (non-streaming)."""
        async with httpx.AsyncClient(timeout=httpx.Timeout(120.0)) as client:
            resp = await client.post(
                f"{self.base_url}/agent/run",
                json={"goal": goal, "stream": False, "maxIterations": 3},
                headers={**self._headers, "x-user-id": user_id},
            )
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return data.get("finalAnswer") or data.get("answer", "Task completed.")

    async def memory_search(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{self.base_url}/memory/search",
                json={"query": query, "topK": top_k},
                headers=self._headers,
            )
            resp.raise_for_status()
            return resp.json().get("data", {}).get("results", [])

    async def skills_list(self) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{self.base_url}/skills", headers=self._headers)
            resp.raise_for_status()
            return resp.json().get("data", {}).get("skills", [])

    async def health(self) -> bool:
        try:
            async with httpx.AsyncClient(timeout=httpx.Timeout(5.0)) as client:
                r = await client.get(f"{self.base_url}/health", headers=self._headers)
                return r.status_code == 200
        except Exception:
            return False
