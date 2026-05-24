"""
Architecture analyzer — extracts high-level structure from indexed code.

Produces:
  - Module tree (package → module → file)
  - Public API surfaces (exported symbols)
  - Service/component boundaries
  - Architecture summary

Based on Codebuff's architecture understanding patterns.
"""

from __future__ import annotations

from typing import Any

from app.code_indexing import vector_store
from app.code_indexing.chunker import CodeChunk
from app.core.logging import get_logger

logger = get_logger(__name__)


async def analyze_architecture() -> dict[str, Any]:
    """Generate a high-level architecture summary of the indexed codebase."""
    status = vector_store.status()
    if status["chunksCount"] == 0:
        return {"status": "empty", "message": "No code indexed yet."}

    # Get all chunks
    all_chunks = await vector_store.search("", top_k=10000)
    if not all_chunks:
        return {"status": "empty"}

    # Build directory tree
    tree: dict[str, Any] = {"name": "<root>", "type": "directory", "children": []}
    dir_map: dict[str, Any] = {"": tree}

    languages: dict[str, int] = {}
    file_count = 0
    all_files: set[str] = set()
    chunk_types: dict[str, int] = {}
    all_symbols: list[str] = []

    for chunk in all_chunks:
        fp = chunk.get("filePath", "")
        lang = chunk.get("language", "unknown")
        ct = chunk.get("chunkType", "unknown")

        languages[lang] = languages.get(lang, 0) + 1
        chunk_types[ct] = chunk_types.get(ct, 0) + 1

        if fp not in all_files:
            all_files.add(fp)
            file_count += 1
            _add_to_tree(tree, dir_map, fp)

        # Collect symbols
        syms = chunk.get("symbols", [])
        all_symbols.extend(syms)

    # Build public API surface
    api_surface = _extract_api_surface(all_chunks)

    return {
        "status": "indexed",
        "summary": {
            "fileCount": file_count,
            "chunkCount": len(all_chunks),
            "languages": dict(sorted(languages.items(), key=lambda x: -x[1])),
            "chunkTypes": chunk_types,
            "symbolCount": len(all_symbols),
        },
        "directoryTree": _simplify_tree(tree),
        "languages": list(languages.keys()),
        "apiSurface": api_surface,
    }


async def analyze_file(file_path: str) -> dict[str, Any] | None:
    """Analyze a specific file in the index."""
    chunks = await vector_store.search_by_file(file_path)
    if not chunks:
        return None

    symbols: list[str] = []
    imports: list[str] = []
    languages = set()

    for c in chunks:
        symbols.extend(c.get("symbols", []))
        imports.extend(c.get("imports", []))
        languages.add(c.get("language", "unknown"))

    return {
        "filePath": file_path,
        "language": next(iter(languages), "unknown"),
        "symbolCount": len(symbols),
        "symbols": symbols[:50],
        "importCount": len(imports),
        "imports": imports[:30],
        "chunkCount": len(chunks),
    }


async def search_architecture(query: str) -> dict[str, Any]:
    """Answer architecture-related questions about the codebase."""
    status = vector_store.status()
    if status["chunksCount"] == 0:
        return {"answer": "No code has been indexed yet. Run /code-index/index first."}

    # Use semantic search to find relevant code
    results = await vector_store.search(query, top_k=15)
    if not results:
        return {"answer": "No relevant code found.", "query": query}

    # Analyze results for patterns
    files_found = set()
    symbols_found = []
    languages_found = set()

    for r in results:
        files_found.add(r.get("filePath", ""))
        symbols_found.extend(r.get("symbols", []))
        languages_found.add(r.get("language", "unknown"))

    return {
        "query": query,
        "answer": f"Found {len(results)} relevant code sections across {len(files_found)} files.",
        "files": sorted(files_found)[:20],
        "symbols": list(set(symbols_found))[:20],
        "languages": list(languages_found),
        "topResults": results[:5],
    }


def _add_to_tree(tree: dict, dir_map: dict, file_path: str) -> None:
    """Add a file to the directory tree structure."""
    parts = file_path.replace("\\", "/").split("/")
    current_path = ""

    for i, part in enumerate(parts):
        parent_path = current_path
        current_path = f"{current_path}/{part}" if current_path else part

        if i == len(parts) - 1:
            # It's a file
            if part not in dir_map:
                parent = dir_map.get(parent_path, tree)
                sibling_names = {c["name"] for c in parent.get("children", [])}
                if part not in sibling_names:
                    parent.setdefault("children", []).append({
                        "name": part,
                        "type": "file",
                    })
        else:
            # It's a directory
            if current_path not in dir_map:
                parent = dir_map.get(parent_path, tree)
                sibling_names = {c["name"] for c in parent.get("children", [])}
                if part not in sibling_names:
                    new_dir = {"name": part, "type": "directory", "children": []}
                    parent.setdefault("children", []).append(new_dir)
                    dir_map[current_path] = new_dir
                else:
                    # Find and use existing
                    for c in parent.get("children", []):
                        if c["name"] == part and c["type"] == "directory":
                            dir_map[current_path] = c
                            break


def _simplify_tree(tree: dict, max_children: int = 50) -> dict:
    """Simplify a tree node for serialization."""
    result = {"name": tree["name"], "type": tree["type"]}
    children = tree.get("children", [])
    if children:
        if len(children) > max_children:
            result["children"] = [_simplify_tree(c) for c in children[:max_children]]
            result["truncated"] = len(children) - max_children
        else:
            result["children"] = [_simplify_tree(c) for c in children]
    return result


def _extract_api_surface(chunks: list[dict]) -> list[dict[str, Any]]:
    """Extract the public API surface from indexed chunks."""
    api_symbols: list[dict[str, Any]] = []

    for chunk in chunks:
        symbols = chunk.get("symbols", [])
        fp = chunk.get("filePath", "")
        lang = chunk.get("language", "unknown")

        for sym in symbols:
            # Heuristic: exported symbols (PascalCase classes, top-level functions)
            if sym.startswith("class ") or sym.startswith("struct ") or sym.startswith("trait "):
                name = sym.split(" ", 1)[1] if " " in sym else sym
                if name and not name.startswith("_"):
                    api_symbols.append({
                        "name": name,
                        "type": "class",
                        "file": fp,
                        "language": lang,
                    })
            elif sym.startswith("def ") or sym.startswith("func ") or sym.startswith("fn "):
                name = sym.split(" ", 1)[1] if " " in sym else sym
                if name and not name.startswith("_"):
                    api_symbols.append({
                        "name": name,
                        "type": "function",
                        "file": fp,
                        "language": lang,
                    })

    return api_symbols[:100]  # limit to 100
