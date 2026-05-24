"""
Code chunker — splits source files into meaningful chunks at
function, class, and module boundaries.

Based on Cocoindex-Code's AST-aware chunking approach with regex-based
boundary detection for 28+ languages.

Chunk types:
  - module    → file-level imports, docstrings, top-level constants
  - class     → class definitions and their methods
  - function  → function / method definitions
  - section   → logical sections separated by comments or blank lines
"""

from __future__ import annotations

import re
from typing import NamedTuple

from app.code_indexing.indexer import IndexableFile


class CodeChunk(NamedTuple):
    """A single chunk of code ready for embedding."""

    id: str                   # unique chunk identifier
    file_path: str            # relative repo path
    language: str             # programming language
    start_line: int           # 1-indexed start line
    end_line: int             # 1-indexed end line (inclusive)
    content: str              # chunk text content
    signature: str            # short signature e.g. "def foo(bar)" or "class UserService"
    chunk_type: str           # "module", "class", "function", "section"
    imports: list[str]        # imports that appear in this chunk
    symbols: list[str]        # symbols defined in this chunk


# ─── Regex patterns per language ──────────────────────────────────────────────

# Python
_RE_FN_PY = re.compile(r"^(async\s+)?def\s+([a-zA-Z_]\w*)\s*\(")
_RE_CLS_PY = re.compile(r"^class\s+([a-zA-Z_]\w*)")
_RE_IMPORT_PY = re.compile(r"^(?:from\s+[\w.]+\s+)?import\s+(.+)$")

# TypeScript / JavaScript
_RE_FN_TS = re.compile(r"^(?:export\s+)?(?:async\s+)?function\s+([a-zA-Z_$]\w*)\s*\(")
_RE_CLS_TS = re.compile(r"^(?:export\s+)?(?:abstract\s+)?class\s+([a-zA-Z_$]\w*)")
_RE_ARROW_FN = re.compile(r"^(?:export\s+)?(?:const|let|var)\s+([a-zA-Z_$]\w*)\s*=\s*(?:async\s*)?\(?")
_RE_IMPORT_TS = re.compile(r"^(?:import\s+|export\s+(?:type\s+)?\{)")

# Go
_RE_FN_GO = re.compile(r"^func\s+(?:\([^)]*\)\s+)?([a-zA-Z_]\w*)\s*\(")
_RE_STRUCT_GO = re.compile(r"^type\s+([a-zA-Z_]\w*)\s+struct")
_RE_INTERFACE_GO = re.compile(r"^type\s+([a-zA-Z_]\w*)\s+interface")
_RE_IMPORT_GO = re.compile(r'^import\s+(?:"|\(|")')

# Rust
_RE_FN_RS = re.compile(r"^(?:pub\s+)?(?:unsafe\s+)?(?:async\s+)?fn\s+([a-zA-Z_]\w*)\s*\(")
_RE_CLS_RS = re.compile(r"^(?:pub\s+)?(?:struct|enum|trait|impl)\s+([a-zA-Z_]\w*)")
_RE_IMPORT_RS = re.compile(r"^use\s+")

# Java / Kotlin
_RE_CLS_JAVA = re.compile(r"^(?:public|private|protected|abstract|final|static)?\s*(?:class|interface|enum|@interface)\s+([a-zA-Z_]\w*)")
_RE_FN_JAVA = re.compile(r"^(?:public|private|protected|static|final|abstract|synchronized|native)?\s*(?:<[^>]+>\s*)?(?:[A-Za-z_]\w*(?:<[^>]+>)?(?:\[\])?\s+)?([a-zA-Z_]\w*)\s*\(")

# C / C++
_RE_FN_C = re.compile(r"^(?:static|inline|virtual|override|extern|const|unsigned|int|void|char|float|double|bool|long|short|size_t|ssize_t|uint\d+_t|int\d+_t|FILE|struct\s+\w+|\w+\s+\*?)\s+([a-zA-Z_]\w*)\s*\(")
_RE_CLS_C = re.compile(r"^class\s+([a-zA-Z_]\w*)")

# Shell
_RE_FN_SH = re.compile(r"^(?:function\s+)?([a-zA-Z_]\w*)\s*\(\)\s*(?:\{|)")

# SQL
_RE_SQL_STMT = re.compile(r"^(CREATE|ALTER|DROP|SELECT|INSERT|UPDATE|DELETE|WITH)\s", re.IGNORECASE)


def chunk_file(file: IndexableFile) -> list[CodeChunk]:
    """Split an IndexableFile into chunks."""
    lines = file.content.splitlines()
    if not lines:
        return []

    lang = file.language
    chunks: list[CodeChunk] = []
    current_start = 0
    current_lines: list[str] = []
    current_imports: list[str] = []
    current_symbols: list[str] = []
    brace_depth = 0
    blank_count = 0
    in_multiline_comment = False

    for i, line in enumerate(lines):
        stripped = line.strip()
        real_line = i + 1  # 1-indexed

        # Skip empty / whitespace only lines
        if not stripped or stripped.isspace():
            blank_count += 1
            # If we've accumulated enough blank lines and have content, flush
            if blank_count >= 2 and current_lines and len(current_lines) > 2:
                end_line = i - blank_count + 1
                chunk = _build_chunk(file, current_lines, current_start + 1, end_line,
                                     current_imports, current_symbols, lang)
                # Only create section-level chunks if they have meaningful content
                if len(current_lines) >= 3 and chunk.symbols:
                    chunk = CodeChunk(
                        id=chunk.id,
                        file_path=chunk.file_path,
                        language=chunk.language,
                        start_line=chunk.start_line,
                        end_line=chunk.end_line,
                        content=chunk.content,
                        signature=chunk.signature,
                        chunk_type="section",
                        imports=chunk.imports,
                        symbols=chunk.symbols,
                    )
                    chunks.append(chunk)
                current_lines = []
                current_start = real_line
                current_imports = []
                current_symbols = []
            continue
        blank_count = 0

        # Detect multi-line comment start/end
        if '"""' in stripped or "'''" in stripped:
            in_multiline_comment = not in_multiline_comment
            current_lines.append(line)
            continue

        # Track brace depth for bracket-based languages
        brace_depth += stripped.count("{") - stripped.count("}")

        # Check if we're at a function or class boundary
        fn_match = _detect_function(stripped, lang)
        cls_match = _detect_class(stripped, lang)

        # Capture imports
        imp = _detect_import(stripped, lang)
        if imp:
            current_imports.append(imp)

        # If we hit a new function/class at top level and have accumulated lines, flush
        if (fn_match or cls_match) and brace_depth <= 1 and current_lines:
            if len(current_lines) >= 2:
                end_line = real_line - 1
                chunks.append(_build_chunk(file, current_lines, current_start + 1,
                                           end_line, current_imports, current_symbols, lang))
                current_lines = []
                current_start = real_line
                current_imports = []
                current_symbols = []

        # Extract symbol name
        symbol = fn_match or cls_match
        if symbol:
            current_symbols.append(symbol)

        current_lines.append(line)

    # Flush remaining lines
    if current_lines:
        chunks.append(_build_chunk(file, current_lines, current_start + 1,
                                   len(lines), current_imports, current_symbols, lang))

    # Fallback: if no chunks (e.g. no functions/classes), create one module-level chunk
    if not chunks:
        chunks.append(_build_chunk(file, lines, 1, len(lines), current_imports,
                                   current_symbols, lang))

    return chunks


def _detect_function(stripped: str, lang: str) -> str | None:
    """Return function name if line is a function definition, else None."""
    if lang == "python":
        m = _RE_FN_PY.match(stripped)
        return f"def {m.group(1)}" if m else None
    elif lang in ("typescript", "typescriptreact", "javascript", "javascriptreact"):
        m = _RE_FN_TS.match(stripped)
        if m:
            return f"function {m.group(1)}"
        m = _RE_ARROW_FN.match(stripped)
        if m and "=>" in stripped:
            return f"const {m.group(1)}"
        return None
    elif lang == "go":
        m = _RE_FN_GO.match(stripped)
        return f"func {m.group(1)}" if m else None
    elif lang == "rust":
        m = _RE_FN_RS.match(stripped)
        return f"fn {m.group(1)}" if m else None
    elif lang in ("java", "kotlin"):
        m = _RE_FN_JAVA.match(stripped)
        return m.group(1) if m else None
    elif lang in ("c", "cpp"):
        m = _RE_FN_C.match(stripped)
        return m.group(1) if m else None
    elif lang == "shell":
        m = _RE_FN_SH.match(stripped)
        return m.group(1) if m else None
    return None


def _detect_class(stripped: str, lang: str) -> str | None:
    """Return class name if line is a class definition, else None."""
    if lang == "python":
        m = _RE_CLS_PY.match(stripped)
        return f"class {m.group(1)}" if m else None
    elif lang in ("typescript", "typescriptreact", "javascript", "javascriptreact"):
        m = _RE_CLS_TS.match(stripped)
        return f"class {m.group(1)}" if m else None
    elif lang == "go":
        m = _RE_STRUCT_GO.match(stripped) or _RE_INTERFACE_GO.match(stripped)
        return m.group(1) if m else None
    elif lang == "rust":
        m = _RE_CLS_RS.match(stripped)
        return m.group(1) if m else None
    elif lang in ("java", "kotlin"):
        m = _RE_CLS_JAVA.match(stripped)
        return m.group(1) if m else None
    elif lang in ("c", "cpp"):
        m = _RE_CLS_C.match(stripped)
        return f"class {m.group(1)}" if m else None
    return None


def _detect_import(stripped: str, lang: str) -> str | None:
    """Return import string if line is an import statement, else None."""
    if lang == "python":
        m = _RE_IMPORT_PY.match(stripped)
        return stripped if m else None
    elif lang in ("typescript", "typescriptreact", "javascript", "javascriptreact"):
        if _RE_IMPORT_TS.match(stripped):
            return stripped
        return None
    elif lang == "go":
        if _RE_IMPORT_GO.match(stripped):
            return stripped
        return None
    elif lang == "rust":
        if _RE_IMPORT_RS.match(stripped):
            return stripped
        return None
    return None


def _build_chunk(
    file: IndexableFile,
    lines: list[str],
    start_line: int,
    end_line: int,
    imports: list[str],
    symbols: list[str],
    lang: str,
) -> CodeChunk:
    """Build a CodeChunk from accumulated lines."""
    content = "\n".join(lines)
    # Clean trailing whitespace
    content = content.rstrip()

    # Determine chunk type
    chunk_type = "section"
    if symbols:
        first = symbols[0]
        if first.startswith("class ") or first.startswith("struct ") or first.startswith("interface ") or first.startswith("trait "):
            chunk_type = "class"
        elif first.startswith("def ") or first.startswith("func ") or first.startswith("fn ") or first.startswith("function "):
            chunk_type = "function"
        elif start_line == 1 and len(lines) <= 20:
            chunk_type = "module"

    # Build signature
    signature = symbols[0] if symbols else f"lines {start_line}-{end_line}"
    if not symbols and imports:
        signature = "<imports>"

    # Unique ID
    chunk_id = f"{file.path}::{start_line}-{end_line}::{signature.replace(' ', '_')}"

    return CodeChunk(
        id=chunk_id,
        file_path=file.path,
        language=lang,
        start_line=start_line,
        end_line=end_line,
        content=content,
        signature=signature,
        chunk_type=chunk_type,
        imports=imports,
        symbols=symbols,
    )
