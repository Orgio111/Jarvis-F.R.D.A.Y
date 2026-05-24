"""
Dependency graph — extracts import-level dependencies between files.

Builds a directed graph where:
  - Nodes = files (relative path)
  - Edges = import relationships

Supports Python, TypeScript/JavaScript, Go, Rust, Java, Kotlin.
"""

from __future__ import annotations

import re
from typing import Any

from app.code_indexing import vector_store
from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── Import pattern per language ──────────────────────────────────────────────

_RE_IMPORT_PY = re.compile(r"^(?:from\s+([\w.]+)\s+)?import\s+(.+)$")
_RE_IMPORT_TS = re.compile(r'''^(?:import\s+(?:\w+\s*,?\s*)?(?:\{[^}]*\})?\s*from\s+['"]([^'"]+)['"]|import\s+['"]([^'"]+)['"])''')
_RE_IMPORT_GO = re.compile(r'^import\s+(?:"(.+)"|\(|"(.+)"$)')
_RE_IMPORT_RS = re.compile(r'^use\s+(.+);?$')
_RE_REQUIRE = re.compile(r'''require\(['"]([^'"]+)['"]\)''')
_RE_DYNAMIC = re.compile(r'''import\(['"]([^'"]+)['"]\)''')


async def build_dependency_graph(
    language: str | None = None,
    depth: int = 2,
) -> dict[str, Any]:
    """Build the dependency graph for all indexed files."""
    status = vector_store.status()
    if status["chunksCount"] == 0:
        return {"status": "empty", "nodes": [], "edges": []}

    all_chunks = await vector_store.search("", top_k=10000)
    if not all_chunks:
        return {"status": "empty"}

    # Build file → imports map
    file_imports: dict[str, list[dict[str, Any]]] = {}
    file_languages: dict[str, str] = {}
    all_files: set[str] = set()

    for chunk in all_chunks:
        fp = chunk.get("filePath", "")
        if not fp:
            continue
        all_files.add(fp)
        file_languages[fp] = chunk.get("language", "unknown")
        if language and file_languages[fp] != language:
            continue

        if fp not in file_imports:
            file_imports[fp] = []

        imports = chunk.get("imports", [])
        lang = file_languages[fp]

        for imp in imports:
            resolved = _resolve_imports(imp, fp, lang)
            file_imports[fp].extend(resolved)

    # Deduplicate imports per file
    for fp in file_imports:
        seen: set[str] = set()
        uniq: list[dict[str, Any]] = []
        for entry in file_imports[fp]:
            target = entry.get("target", "")
            if target not in seen:
                seen.add(target)
                uniq.append(entry)
        file_imports[fp] = uniq

    # Build nodes and edges
    nodes = []
    edges = []

    for fp in sorted(all_files):
        nodes.append({
            "id": fp,
            "label": fp.split("/")[-1],
            "language": file_languages.get(fp, "unknown"),
            "importCount": len(file_imports.get(fp, [])),
        })

    for source_fp, targets in file_imports.items():
        for t in targets:
            target = t["target"]
            if target in all_files:
                edges.append({
                    "source": source_fp,
                    "target": target,
                    "type": t.get("type", "import"),
                })

    return {
        "status": "indexed",
        "nodeCount": len(nodes),
        "edgeCount": len(edges),
        "nodes": nodes,
        "edges": edges,
    }


async def get_dependencies(file_path: str) -> dict[str, Any]:
    """Get dependencies for a specific file."""
    deps = await _get_file_deps(file_path)
    return {
        "filePath": file_path,
        "imports": deps.get("imports", []),
        "importedBy": deps.get("importedBy", []),
        "language": deps.get("language", "unknown"),
    }


async def _get_file_deps(file_path: str) -> dict[str, Any]:
    """Internal: get both incoming and outgoing dependencies."""
    graph = await build_dependency_graph()
    if graph["status"] == "empty":
        return {"imports": [], "importedBy": []}

    # Outgoing edges
    imports = [
        e["target"] for e in graph.get("edges", [])
        if e["source"] == file_path
    ]

    # Incoming edges
    imported_by = [
        e["source"] for e in graph.get("edges", [])
        if e["target"] == file_path
    ]

    return {
        "filePath": file_path,
        "imports": list(set(imports)),
        "importedBy": list(set(imported_by)),
    }


def _resolve_imports(
    imp_line: str,
    source_file: str,
    language: str,
) -> list[dict[str, Any]]:
    """Resolve an import line to target file paths."""
    results: list[dict[str, Any]] = []
    source_dir = "/".join(source_file.split("/")[:-1]) if "/" in source_file else ""

    if language == "python":
        return _resolve_python(imp_line, source_dir)
    elif language in ("typescript", "typescriptreact", "javascript", "javascriptreact"):
        return _resolve_ts(imp_line, source_dir)
    elif language == "go":
        return _resolve_go(imp_line, source_dir)
    elif language == "rust":
        return _resolve_rust(imp_line, source_dir)
    else:
        return results


def _resolve_python(imp_line: str, source_dir: str) -> list[dict[str, Any]]:
    results = []
    m = _RE_IMPORT_PY.match(imp_line)
    if m:
        module = m.group(1) or ""
        names = m.group(2)
        if module:
            # from X import Y → target module is X
            target = module.replace(".", "/") + ".py"
            results.append({"target": target, "type": "import", "symbol": names.strip()})
        else:
            # import X → target module is X
            for name in names.split(","):
                name = name.strip().split(" ")[0].split(".")[0]
                if name:
                    results.append({
                        "target": name.replace(".", "/") + ".py",
                        "type": "import",
                    })
    return results


def _resolve_ts(imp_line: str, source_dir: str) -> list[dict[str, Any]]:
    results = []
    m = _RE_IMPORT_TS.match(imp_line)
    if m:
        target = m.group(1) or m.group(2) or ""
        target = target.strip()
        if target and not target.startswith("."):
            # External package — don't resolve
            return results
        if target:
            # Resolve relative path
            resolved = _resolve_rel_path(target, source_dir)
            if resolved:
                results.append({"target": resolved, "type": "import"})
    return results


def _resolve_go(imp_line: str, source_dir: str) -> list[dict[str, Any]]:
    results = []
    m = _RE_IMPORT_GO.match(imp_line)
    if m:
        target = m.group(1) or m.group(2) or ""
        # Only resolve local imports
        if target.startswith('"'):
            target = target.strip('"')
        if target and not "." in target and not target.startswith("/"):
            results.append({"target": target, "type": "import"})
    return results


def _resolve_rust(imp_line: str, source_dir: str) -> list[dict[str, Any]]:
    results = []
    m = _RE_IMPORT_RS.match(imp_line)
    if m:
        target = m.group(1).strip(";").strip()
        if "::" in target:
            target = target.replace("::", "/")
        if target and not target.startswith("extern"):
            results.append({"target": target, "type": "import"})
    return results


def _resolve_rel_path(import_path: str, source_dir: str) -> str:
    """Resolve a relative import path (e.g., '../foo/bar') to a file path."""
    if not import_path.startswith("."):
        return import_path

    parts = source_dir.split("/") if source_dir else []
    import_parts = import_path.split("/")

    # Count dots
    dots = 0
    for p in import_parts:
        if p == "..":
            dots += 1
        elif p == ".":
            continue
        else:
            break

    # Remove dots from the front
    base_parts = import_parts[dots:]

    # Go up from source directory
    if dots > 0 and len(parts) >= dots:
        parts = parts[:-dots]

    resolved = "/".join(parts + base_parts)
    # Try common extensions
    for ext in [".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs"]:
        if not any(resolved.endswith(e) for e in [".ts", ".tsx", ".js", ".jsx", ".py", ".go", ".rs"]):
            candidate = resolved + ext
            # We just return the best guess
        else:
            candidate = resolved
            break
    else:
        candidate = resolved

    return candidate
