from __future__ import annotations

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.core.config import get_settings
from app.core.envelopes import error, success
from app.core.logging import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.post("/search")
async def web_search(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()

    if not settings.web_search_enabled:
        return JSONResponse(
            status_code=503,
            content=error("search_disabled", "Web search is disabled", correlation_id=correlation_id),
        )

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Request body must be valid JSON", correlation_id=correlation_id),
        )

    query: str = body.get("query", "").strip()
    max_results: int = min(int(body.get("maxResults", 5)), 20)

    if not query:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "query is required", correlation_id=correlation_id),
        )

    results = await _search_ddg(query, max_results)
    return success(
        {
            "query": query,
            "results": results,
            "total": len(results),
            "engine": "duckduckgo",
        },
        correlation_id,
    )


@router.get("/search/status")
async def search_status(request: Request) -> dict:
    correlation_id = request.headers.get("x-correlation-id")
    settings = get_settings()
    return success(
        {
            "enabled": settings.web_search_enabled,
            "deepSearchEnabled": settings.deep_search_enabled,
            "engine": "duckduckgo",
        },
        correlation_id,
    )


async def _search_ddg(query: str, max_results: int) -> list[dict]:
    """Lightweight DuckDuckGo instant-answer scrape — no API key needed."""
    try:
        params = {
            "q": query,
            "format": "json",
            "no_html": "1",
            "skip_disambig": "1",
        }
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get("https://api.duckduckgo.com/", params=params)
        if r.status_code != 200:
            return _fallback_results(query)

        data = r.json()
        results: list[dict] = []

        # AbstractText (knowledge panel)
        if data.get("AbstractText"):
            results.append({
                "title": data.get("Heading", query),
                "snippet": data["AbstractText"][:500],
                "url": data.get("AbstractURL", ""),
                "source": data.get("AbstractSource", ""),
                "type": "abstract",
            })

        # RelatedTopics
        for topic in data.get("RelatedTopics", [])[:max_results]:
            if isinstance(topic, dict) and topic.get("Text") and topic.get("FirstURL"):
                results.append({
                    "title": topic["Text"][:80],
                    "snippet": topic["Text"][:300],
                    "url": topic["FirstURL"],
                    "source": "DuckDuckGo",
                    "type": "related",
                })
            if len(results) >= max_results:
                break

        return results if results else _fallback_results(query)
    except Exception as exc:
        logger.warning("search_ddg_failed", error=str(exc))
        return _fallback_results(query)


def _fallback_results(query: str) -> list[dict]:
    return [
        {
            "title": f"Search for '{query}' on DuckDuckGo",
            "snippet": "Web search is available but the result could not be parsed. Visit DuckDuckGo directly.",
            "url": f"https://duckduckgo.com/?q={query.replace(' ', '+')}",
            "source": "DuckDuckGo",
            "type": "fallback",
        }
    ]
