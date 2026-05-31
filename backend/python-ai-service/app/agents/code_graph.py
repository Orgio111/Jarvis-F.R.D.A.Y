"""CodeGraph — AST-based import/dependency graph for a codebase.

Supports:
  - Python  (.py)  — ast.parse() → Import / ImportFrom nodes
  - JS/TS   (.js .ts .jsx .tsx .mjs .cjs) — regex on import/require statements

Usage:
    graph = CodeGraph.build(repo_root)
    deps  = graph.dependencies("src/agents/editor.py")      # direct imports
    reach = graph.reachable(["src/agents/editor.py"], hops=2) # transitive

Design (graphify / cocoindex-code pattern):
  - Pure stdlib — no extra deps
  - O(files) build time; results cached per repo_root
  - Falls back gracefully: unparseable files get empty dep list
"""
from __future__ import annotations

import ast
import os
import re
from collections import deque
from functools import lru_cache
from pathlib import Path
from typing import Optional

_PY_EXTS  = {".py", ".pyw"}
_JS_EXTS  = {".js", ".ts", ".jsx", ".tsx", ".mjs", ".cjs"}
_ALL_EXTS = _PY_EXTS | _JS_EXTS

# Regex for JS/TS imports — catches:
#   import ... from './foo'
#   import('./bar')
#   require('./baz')
_JS_IMPORT_RE = re.compile(
    r"""(?:import\s+.*?from\s+|import\s*\(|require\s*\()\s*['"`]([^'"`]+)['"`]""",
    re.MULTILINE,
)

# Max file size to parse (skip huge generated files)
_MAX_PARSE_BYTES = 256 * 1024


class CodeGraph:
    """Directed graph: file → set of files it imports."""

    def __init__(self, root: str, graph: dict[str, set[str]]):
        self.root  = root
        self._graph = graph  # {relative_path → {relative_path, ...}}

    # ── Build ─────────────────────────────────────────────────────────────────

    @classmethod
    def build(cls, repo_root: str) -> "CodeGraph":
        """Walk repo_root, parse every source file, return graph."""
        root = Path(repo_root).resolve()
        graph: dict[str, set[str]] = {}

        # Index all source files for fast resolution
        all_files: set[str] = set()
        for dirpath, dirnames, filenames in os.walk(root):
            # Skip common noise dirs
            dirnames[:] = [
                d for d in dirnames
                if d not in {
                    ".git", "__pycache__", "node_modules", ".venv",
                    "venv", "dist", "build", ".next", ".nuxt", "coverage",
                }
            ]
            for fname in filenames:
                ext = Path(fname).suffix.lower()
                if ext in _ALL_EXTS:
                    rel = str(Path(dirpath, fname).relative_to(root))
                    all_files.add(rel)
                    graph[rel] = set()

        # Parse each file
        for rel in list(all_files):
            abs_path = root / rel
            ext = Path(rel).suffix.lower()
            try:
                raw = abs_path.read_bytes()
                if len(raw) > _MAX_PARSE_BYTES:
                    continue
                text = raw.decode("utf-8", errors="replace")
                if ext in _PY_EXTS:
                    deps = cls._parse_python(text, rel, root, all_files)
                else:
                    deps = cls._parse_js(text, rel, root, all_files)
                graph[rel] = deps
            except Exception:
                pass  # keep empty set for unparseable files

        return cls(str(root), graph)

    # ── Query ─────────────────────────────────────────────────────────────────

    def dependencies(self, path: str, hops: int = 1) -> list[str]:
        """Files directly (or transitively up to `hops`) imported by `path`."""
        return list(self.reachable([path], hops=hops) - {path})

    def dependents(self, path: str) -> list[str]:
        """Files that import `path` (reverse edges)."""
        return [f for f, deps in self._graph.items() if path in deps]

    def reachable(self, seeds: list[str], hops: int = 2) -> set[str]:
        """BFS from seed files, up to `hops` levels deep."""
        visited: set[str] = set()
        queue: deque[tuple[str, int]] = deque((s, 0) for s in seeds if s in self._graph)
        while queue:
            node, depth = queue.popleft()
            if node in visited:
                continue
            visited.add(node)
            if depth < hops:
                for dep in self._graph.get(node, set()):
                    if dep not in visited:
                        queue.append((dep, depth + 1))
        return visited

    def most_connected(self, candidates: list[str], top_n: int = 5) -> list[str]:
        """Return top_n candidates sorted by out-degree + in-degree (hub score)."""
        def score(f: str) -> int:
            out = len(self._graph.get(f, set()))
            in_ = sum(1 for deps in self._graph.values() if f in deps)
            return out + in_

        return sorted(candidates, key=score, reverse=True)[:top_n]

    def all_files(self) -> list[str]:
        return list(self._graph.keys())

    # ── Parsers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _parse_python(
        source: str,
        rel_path: str,
        root: Path,
        all_files: set[str],
    ) -> set[str]:
        """Extract imported module paths from Python source."""
        try:
            tree = ast.parse(source, filename=rel_path)
        except SyntaxError:
            return set()

        pkg_dir = str(Path(rel_path).parent)
        deps: set[str] = set()

        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    resolved = CodeGraph._resolve_py_module(
                        alias.name, pkg_dir, root, all_files, relative=False
                    )
                    if resolved:
                        deps.add(resolved)

            elif isinstance(node, ast.ImportFrom):
                if node.module is None:
                    continue
                level = node.level or 0
                resolved = CodeGraph._resolve_py_module(
                    node.module, pkg_dir, root, all_files, relative=(level > 0)
                )
                if resolved:
                    deps.add(resolved)

        return deps

    @staticmethod
    def _resolve_py_module(
        module: str,
        pkg_dir: str,
        root: Path,
        all_files: set[str],
        relative: bool,
    ) -> Optional[str]:
        """Try to find a .py file matching a module name."""
        parts = module.replace(".", os.sep)
        candidates = []
        if relative:
            candidates.append(os.path.join(pkg_dir, parts + ".py"))
            candidates.append(os.path.join(pkg_dir, parts, "__init__.py"))
        # Absolute from root
        candidates.append(parts + ".py")
        candidates.append(os.path.join(parts, "__init__.py"))

        for c in candidates:
            norm = c.replace("\\", "/")
            if norm in all_files:
                return norm
        return None

    @staticmethod
    def _parse_js(
        source: str,
        rel_path: str,
        root: Path,
        all_files: set[str],
    ) -> set[str]:
        """Extract imported file paths from JS/TS source."""
        pkg_dir = str(Path(rel_path).parent)
        deps: set[str] = set()

        for m in _JS_IMPORT_RE.finditer(source):
            spec = m.group(1)
            # Only resolve relative imports (starts with . or ..)
            if not spec.startswith("."):
                continue
            resolved = CodeGraph._resolve_js_spec(spec, pkg_dir, all_files)
            if resolved:
                deps.add(resolved)

        return deps

    @staticmethod
    def _resolve_js_spec(
        spec: str,
        pkg_dir: str,
        all_files: set[str],
    ) -> Optional[str]:
        """Resolve a relative JS/TS import specifier to a repo-relative path."""
        base = os.path.normpath(os.path.join(pkg_dir, spec)).replace("\\", "/")
        # Try exact
        if base in all_files:
            return base
        # Try adding extensions
        for ext in (".ts", ".tsx", ".js", ".jsx", ".mjs"):
            c = base + ext
            if c in all_files:
                return c
        # Try index file
        for ext in (".ts", ".tsx", ".js", ".jsx"):
            c = base + "/index" + ext
            if c in all_files:
                return c
        return None
