"""
Search orchestrator — combines semantic (vector), symbol, and keyword search
into a unified result set.

Inspired by Codebuff's file-picker agent and Cocoindex-Code's MCP search.
"""

from __future__ import annotations

import re
import fnmatch
from typing import Any

from app.code_indexing import vector_store
from app.core.logging import get_logger

logger = get_logger(__name__)


async def unified_search(
    query: str,
    top_k: int = 10,
    language: str | None = None,
    chunk_type: str | None = None,
    include_semantic: bool = True,
    include_symbol: bool = True,
) -> dict[str, Any]:
    """
    Multi-strategy code search.

    Returns merged results with deduplication.
    """
    seen: set[str] = set()
    all_results: list[dict[str, Any]] = []

    # 1. Semantic search (vector)
    semantic_results: list[dict[str, Any]] = []
    if include_semantic:
        try:
            semantic_results = await vector_store.search(
                query, top_k=top_k * 2,
                language=language, chunk_type=chunk_type,
            )
            for r in semantic_results:
                if r["chunkId"] not in seen:
                    r["searchMethod"] = "semantic"
                    all_results.append(r)
                    seen.add(r["chunkId"])
        except Exception as exc:
            logger.warning("semantic_search_failed", error=str(exc))

    # 2. Symbol search (if query looks like a symbol)
    if include_symbol and _looks_like_symbol(query):
        try:
            symbol_results = await vector_store.search_by_symbol(query, language=language)
            for r in symbol_results:
                if r["chunkId"] not in seen:
                    r["searchMethod"] = "symbol"
                    all_results.append(r)
                    seen.add(r["chunkId"])
        except Exception as exc:
            logger.warning("symbol_search_failed", error=str(exc))

    # 3. If semantic returned nothing, try keyword-like matching
    if not all_results:
        try:
            # Simple keyword fallback — scan chunk content for query words
            all_chunks = await vector_store.search_by_file("*")
            if not all_chunks:
                # Try a broad semantic query as last resort
                fallback = await vector_store.search(
                    query, top_k=5,
                    language=language, chunk_type=chunk_type,
                )
                for r in fallback:
                    if r["chunkId"] not in seen:
                        r["searchMethod"] = "fallback"
                        all_results.append(r)
                        seen.add(r["chunkId"])
        except Exception as exc:
            logger.warning("fallback_search_failed", error=str(exc))

    # Sort by score descending
    all_results.sort(key=lambda r: r.get("score", 0), reverse=True)

    return {
        "query": query,
        "total": len(all_results),
        "results": all_results[:top_k],
        "methods": {
            "semantic": len(semantic_results),
            "symbol": sum(1 for r in all_results if r.get("searchMethod") == "symbol"),
        },
    }


async def file_search(
    pattern: str,
    language: str | None = None,
) -> list[dict[str, Any]]:
    """Search for files matching a glob or regex pattern."""
    import fnmatch
    from app.code_indexing import vector_store as vs

    status = vs.status()
    if status["chunksCount"] == 0:
        return []

    # Get all unique file paths from chunks
    # We do this via a broad search
    all_chunks = await vs.search("", top_k=10000)
    seen_files: set[str] = set()
    results: list[dict[str, Any]] = []

    for chunk in all_chunks:
        fp = chunk.get("filePath", "")
        if fp in seen_files:
            continue
        if fnmatch.fnmatch(fp, pattern):
            if language:
                if chunk.get("language") != language:
                    continue
            seen_files.add(fp)
            results.append({
                "filePath": fp,
                "language": chunk.get("language", "unknown"),
                "matchedPattern": pattern,
            })

    return results


def _looks_like_symbol(query: str) -> bool:
    """Heuristic: does the query look like a symbol name?"""
    # Remove whitespace
    q = query.strip()
    if not q:
        return False

    # Single word, PascalCase, camelCase, snake_case, or dotted path
    symbol_patterns = [
        r"^[A-Z][a-zA-Z0-9]+$",         # PascalCase
        r"^[a-z]+[A-Z][a-zA-Z0-9]*$",   # camelCase
        r"^[a-z][a-z0-9]*(_[a-z0-9]+)*$",  # snake_case
        r"^[A-Z][A-Z0-9]*(_[A-Z0-9]+)*$",  # SCREAMING_SNAKE_CASE
        r"^[a-zA-Z_]\w*\.\w+$",         # dotted.path
        r"^[a-zA-Z_]\w*\(\)$",          # function()
    ]
    return any(re.match(p, q) for p in symbol_patterns)
