"""
FastAPI router for code indexing — /code-index/* endpoints.

Endpoints:
  POST /code-index/index          — Walk repo + chunk + embed + index
  POST /code-index/search          — Unified semantic + symbol search
  GET  /code-index/status          — Index status
  DELETE /code-index/clear         — Wipe index
  GET  /code-index/analyze         — Architecture analysis
  GET  /code-index/analyze/file    — Single-file analysis
  POST /code-index/analyze/search  — Architecture Q&A
  GET  /code-index/dependencies    — Dependency graph
  GET  /code-index/dependencies/file — Single-file deps
  POST /code-index/index/incremental — Incremental update
"""

from __future__ import annotations

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.code_indexing import vector_store
from app.code_indexing.indexer import walk_repo
from app.code_indexing.chunker import chunk_file
from app.code_indexing.embedder import load_embedder
from app.code_indexing.search import unified_search
from app.code_indexing.analyzer import analyze_architecture, analyze_file, search_architecture
from app.code_indexing.dependency_graph import build_dependency_graph, get_dependencies
from app.core.envelopes import error, success

router = APIRouter(prefix="/code-index")


@router.post("/index")
async def index_repo(request: Request) -> dict:
    """Walk the repo, chunk all files, embed chunks, and add to FAISS index."""
    correlation_id = request.headers.get("x-correlation-id")

    try:
        body = await request.json()
    except Exception:
        body = {}

    repo_path: str | None = body.get("repoPath")
    force: bool = body.get("force", False)
    max_files: int = min(int(body.get("maxFiles", 5000)), 20000)

    # Load embedder
    embed_ok = await load_embedder()
    if not embed_ok:
        return JSONResponse(
            status_code=503,
            content=error("embedder_unavailable",
                          "Embedding model could not be loaded. Check that sentence-transformers is installed.",
                          correlation_id=correlation_id),
        )

    # Init vector store
    init_ok = await vector_store.init_index(force_rebuild=force)
    if not init_ok:
        return JSONResponse(
            status_code=503,
            content=error("index_unavailable",
                          "Vector store (FAISS) could not be initialized.",
                          correlation_id=correlation_id),
        )

    if force:
        await vector_store.clear()
        await vector_store.init_index(force_rebuild=True)

    # Walk repo
    total_chunks = 0
    total_files = 0
    import asyncio
    async for file in walk_repo(repo_path=repo_path, max_files=max_files):
        chunks = chunk_file(file)
        added = await vector_store.add_chunks(chunks)
        total_chunks += added
        total_files += 1

        # Yield control every 10 files
        if total_files % 10 == 0:
            await asyncio.sleep(0)

    return success({
        "indexed": True,
        "filesProcessed": total_files,
        "chunksIndexed": total_chunks,
        "vectorCount": vector_store.status()["vectorCount"],
    }, correlation_id)


@router.post("/search")
async def search_code(request: Request) -> dict:
    """Unified semantic + symbol code search."""
    correlation_id = request.headers.get("x-correlation-id")

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Request body must be valid JSON", correlation_id=correlation_id),
        )

    query = (body.get("query") or "").strip()
    top_k = min(int(body.get("topK", 10)), 100)
    language = body.get("language")
    chunk_type = body.get("chunkType")
    include_semantic = body.get("includeSemantic", True)
    include_symbol = body.get("includeSymbol", True)

    if not query:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "query is required", correlation_id=correlation_id),
        )

    results = await unified_search(
        query=query,
        top_k=top_k,
        language=language,
        chunk_type=chunk_type,
        include_semantic=include_semantic,
        include_symbol=include_symbol,
    )
    return success(results, correlation_id)


@router.get("/status")
async def index_status(request: Request) -> dict:
    """Get current index status."""
    correlation_id = request.headers.get("x-correlation-id")
    return success(vector_store.status(), correlation_id)


@router.delete("/clear")
async def clear_index(request: Request) -> dict:
    """Wipe the entire code index."""
    correlation_id = request.headers.get("x-correlation-id")
    await vector_store.clear()
    return success({"cleared": True}, correlation_id)


@router.get("/analyze")
async def get_architecture(request: Request) -> dict:
    """Get full architecture analysis."""
    correlation_id = request.headers.get("x-correlation-id")
    analysis = await analyze_architecture()
    return success(analysis, correlation_id)


@router.get("/analyze/file")
async def get_file_analysis(request: Request, filePath: str = "") -> dict:
    """Analyze a specific file."""
    correlation_id = request.headers.get("x-correlation-id")
    if not filePath:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "filePath query parameter is required", correlation_id=correlation_id),
        )
    analysis = await analyze_file(filePath)
    if analysis is None:
        return JSONResponse(
            status_code=404,
            content=error("not_found", f"File '{filePath}' not found in index", correlation_id=correlation_id),
        )
    return success(analysis, correlation_id)


@router.post("/analyze/search")
async def architecture_search(request: Request) -> dict:
    """Answer architecture questions about the codebase."""
    correlation_id = request.headers.get("x-correlation-id")
    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "Request body must be valid JSON", correlation_id=correlation_id),
        )
    query = (body.get("query") or "").strip()
    if not query:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "query is required", correlation_id=correlation_id),
        )
    result = await search_architecture(query)
    return success(result, correlation_id)


@router.get("/dependencies")
async def get_dependency_graph(request: Request) -> dict:
    """Get the full dependency graph."""
    correlation_id = request.headers.get("x-correlation-id")
    lang = request.query_params.get("language")
    depth = int(request.query_params.get("depth", 2))
    graph = await build_dependency_graph(language=lang, depth=depth)
    return success(graph, correlation_id)


@router.get("/dependencies/file")
async def get_file_dependencies(request: Request, filePath: str = "") -> dict:
    """Get dependencies for a specific file."""
    correlation_id = request.headers.get("x-correlation-id")
    if not filePath:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "filePath query parameter is required", correlation_id=correlation_id),
        )
    deps = await get_dependencies(filePath)
    return success(deps, correlation_id)


@router.post("/index/incremental")
async def incremental_index(request: Request) -> dict:
    """Incremental index update — only processes changed files."""
    correlation_id = request.headers.get("x-correlation-id")

    try:
        body = await request.json()
    except Exception:
        body = {}

    changed_files: list[str] = body.get("changedFiles", [])
    if not changed_files:
        return JSONResponse(
            status_code=400,
            content=error("invalid_request", "changedFiles list is required", correlation_id=correlation_id),
        )

    embed_ok = await load_embedder()
    if not embed_ok:
        return JSONResponse(
            status_code=503,
            content=error("embedder_unavailable",
                          "Embedding model could not be loaded.", correlation_id=correlation_id),
        )

    await vector_store.init_index()
    total_added = 0
    import asyncio
    from app.code_indexing.indexer import walk_repo, IndexableFile

    async for file in walk_repo(max_files=5000):
        if file.path in changed_files:
            chunks = chunk_file(file)
            added = await vector_store.add_chunks(chunks)
            total_added += added
            await asyncio.sleep(0)

    return success({
        "incremental": True,
        "filesProcessed": len(changed_files),
        "chunksAdded": total_added,
    }, correlation_id)
