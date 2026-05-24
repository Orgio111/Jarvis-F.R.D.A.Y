"""
Repo walker — crawls a directory tree, respects .gitignore / .jarvisignore,
yields IndexableFile objects for the chunker pipeline.

Based on patterns from Codebuff (file-picker agent) and Cocoindex-Code (Rust crawler).
"""

from __future__ import annotations

import os
import re
import fnmatch
from enum import Enum
from pathlib import Path
from typing import AsyncIterator, NamedTuple

from app.core.logging import get_logger

logger = get_logger(__name__)

# ─── Supported language extensions ────────────────────────────────────────────

_LANG_MAP: dict[str, str] = {
    # Python
    ".py": "python",
    ".pyi": "python",
    ".pyx": "python",
    # TypeScript / JavaScript
    ".ts": "typescript",
    ".tsx": "typescriptreact",
    ".js": "javascript",
    ".jsx": "javascriptreact",
    ".mjs": "javascript",
    ".cjs": "javascript",
    # Go
    ".go": "go",
    # Rust
    ".rs": "rust",
    # Java
    ".java": "java",
    ".kt": "kotlin",
    ".kts": "kotlin",
    # C / C++
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".hpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    # Web / config
    ".css": "css",
    ".scss": "scss",
    ".html": "html",
    ".htm": "html",
    ".json": "json",
    ".yaml": "yaml",
    ".yml": "yaml",
    ".xml": "xml",
    ".md": "markdown",
    ".sql": "sql",
    ".sh": "shell",
    ".bash": "shell",
    ".zsh": "shell",
    ".ps1": "powershell",
    ".dockerfile": "dockerfile",
    ".tf": "terraform",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".proto": "protobuf",
}

# Patterns always ignored (even if not in .gitignore)
_ALWAYS_IGNORE: list[str] = [
    ".git/",
    ".svn/",
    "__pycache__/",
    "node_modules/",
    "venv/",
    ".venv/",
    ".env",
    ".env.*",
    ".jarvisignore",
    ".gitignore",
    "*.pyc",
    "*.pyo",
    "*.so",
    "*.dll",
    "*.dylib",
    "*.exe",
    "*.bin",
    "*.class",
    "*.jar",
    "*.png",
    "*.jpg",
    "*.jpeg",
    "*.gif",
    "*.svg",
    "*.ico",
    "*.woff",
    "*.woff2",
    "*.ttf",
    "*.eot",
    "*.mp4",
    "*.mp3",
    "*.wav",
    "*.ogg",
    "*.webm",
    "*.zip",
    "*.tar",
    "*.gz",
    "*.bz2",
    "*.7z",
    "*.pak",
    ".DS_Store",
    "Thumbs.db",
    "*.lock",
    "package-lock.json",
    "yarn.lock",
    "pnpm-lock.yaml",
    ".gitkeep",
    ".dockerignore",
    ".editorconfig",
    ".prettierrc*",
    ".eslintrc*",
    ".claude/",
    ".cocoindex_code/",
    "data/",
    "tmp/",
    ".mypy_cache/",
    ".ruff_cache/",
    ".pytest_cache/",
    "*.egg-info/",
    "dist/",
    "build/",
    "__pycache__/",
]

# Maximum file size to index (1 MB)
_MAX_FILE_BYTES = 1_048_576


class FileType(Enum):
    SOURCE = "source"
    CONFIG = "config"
    DOCUMENTATION = "documentation"
    DATA = "data"
    UNKNOWN = "unknown"


class IndexableFile(NamedTuple):
    """A file ready for chunking."""

    path: str                # relative repo path e.g. "src/main.py"
    absolute_path: str       # full OS path
    language: str            # programming language identifier
    file_type: FileType
    size_bytes: int
    content: str


# ─── .jarvisignore parser ─────────────────────────────────────────────────────

def _load_ignore_patterns(root: Path) -> list[str]:
    """Load .jarvisignore from project root if it exists."""
    ignore_file = root / ".jarvisignore"
    patterns: list[str] = []
    if ignore_file.exists():
        try:
            text = ignore_file.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    patterns.append(stripped)
        except Exception as exc:
            logger.warning("jarvisignore_read_failed", error=str(exc))
    return patterns


def _load_gitignore(root: Path) -> list[str]:
    """Load .gitignore from project root if it exists."""
    ignore_file = root / ".gitignore"
    patterns: list[str] = []
    if ignore_file.exists():
        try:
            text = ignore_file.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    patterns.append(stripped)
        except Exception as exc:
            logger.warning("gitignore_read_failed", error=str(exc))
    return patterns


def _is_ignored(rel_path: str, patterns: list[str]) -> bool:
    """Check if a relative path matches any of the ignore glob patterns."""
    for pat in patterns:
        # Directory patterns end with /
        if pat.endswith("/"):
            if rel_path.startswith(pat) or rel_path == pat.rstrip("/"):
                return True
            # Also check if any part of the path matches
            parts = rel_path.split("/")
            if pat.rstrip("/") in parts:
                return True
            continue
        # File patterns
        if fnmatch.fnmatch(rel_path, pat):
            return True
        # Also match just the filename if it's a simple pattern
        if "/" not in pat and "/" in rel_path:
            if fnmatch.fnmatch(Path(rel_path).name, pat):
                return True
    return False


# ─── Public API ───────────────────────────────────────────────────────────────

async def walk_repo(
    repo_path: str | None = None,
    max_files: int = 5000,
) -> AsyncIterator[IndexableFile]:
    """
    Walk a repository directory and yield IndexableFile objects.

    Parameters
    ----------
    repo_path : str, optional
        Root directory. Defaults to the current project root (three levels up from the service).
    max_files : int
        Maximum number of files to index (safety limit).

    Yields
    ------
    IndexableFile objects ready for chunking.
    """
    if repo_path is None:
        # Walk up from this file's location to find project root
        # Service is at backend/python-ai-service/app/code_indexing/
        # Project root is 4 levels up
        repo_path = str(Path(__file__).resolve().parent.parent.parent.parent.parent.parent)

    root = Path(project_root(repo_path)).resolve()

    # Load ignore patterns
    always_ignore = list(_ALWAYS_IGNORE)
    always_ignore.extend(_load_gitignore(root))
    always_ignore.extend(_load_jarvisignore(root))

    count = 0
    for dirpath_str, dirnames, filenames in os.walk(str(root), topdown=True):
        # Relative path within repo
        rel_dir = os.path.relpath(dirpath_str, str(root))
        rel_dir = "." if rel_dir == "." else rel_dir.replace("\\", "/")

        # Filter directories in-place (mutating dirnames affects os.walk)
        filtered_dirs: list[str] = []
        for d in dirnames:
            rel_d = f"{rel_dir}/{d}" if rel_dir != "." else d
            if _is_ignored(rel_d + "/", always_ignore):
                continue
            filtered_dirs.append(d)
        dirnames[:] = filtered_dirs

        for fname in filenames:
            rel_file = f"{rel_dir}/{fname}" if rel_dir != "." else fname

            # Skip ignored
            if _is_ignored(rel_file, always_ignore):
                continue

            fpath = os.path.join(dirpath_str, fname)

            # Skip symlinks, special files
            if not os.path.isfile(fpath):
                continue

            # Size check
            size = os.path.getsize(fpath)
            if size > _MAX_FILE_BYTES:
                continue
            if size == 0:
                continue

            # Language detection
            ext = os.path.splitext(fname)[1].lower()
            # Handle .dockerfile
            if fname.lower() == "dockerfile" or fname.lower() == "containerfile":
                ext = ".dockerfile"
            lang = _LANG_MAP.get(ext, "unknown")

            if lang == "unknown":
                continue  # skip binary / unknown extensions

            # Read content
            try:
                content = read_file_safe(fpath)
            except Exception:
                continue

            if not content.strip():
                continue

            # Classify file type
            file_type = _classify_file(fname, lang)

            count += 1
            yield IndexableFile(
                path=rel_file,
                absolute_path=fpath,
                language=lang,
                file_type=file_type,
                size_bytes=size,
                content=content,
            )

            if count >= max_files:
                logger.warning("walk_repo_max_files_reached", max_files=max_files)
                return

    logger.info("walk_repo_complete", files_indexed=count)


def project_root(start_path: str | None = None) -> str:
    """Find the project root by looking for a marker file (e.g. .gitignore, Makefile, README.md)."""
    search_path = Path(start_path or os.getcwd()).resolve()
    markers = {".gitignore", "Makefile", "README.md", "Cargo.toml", "pyproject.toml"}
    for parent in [search_path] + list(search_path.parents):
        if any((parent / m).exists() for m in markers):
            return str(parent)
    return str(search_path)


def read_file_safe(fpath: str) -> str:
    """Read a file with multiple encoding fallbacks."""
    encodings = ["utf-8", "utf-8-sig", "latin-1", "cp1252"]
    for enc in encodings:
        try:
            with open(fpath, "r", encoding=enc, errors="strict") as f:
                return f.read()
        except (UnicodeDecodeError, UnicodeError):
            continue
    # Last resort: ignore errors
    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
        return f.read()


def _load_jarvisignore(root: Path) -> list[str]:
    ignore_file = root / ".jarvisignore"
    patterns: list[str] = []
    if ignore_file.exists():
        try:
            text = ignore_file.read_text(encoding="utf-8", errors="ignore")
            for line in text.splitlines():
                stripped = line.strip()
                if stripped and not stripped.startswith("#"):
                    patterns.append(stripped)
        except Exception as exc:
            logger.warning("jarvisignore_read_failed", error=str(exc))
    return patterns


def _classify_file(fname: str, language: str) -> FileType:
    """Classify a file by its type based on name and extension."""
    if language in ("python", "typescript", "typescriptreact", "javascript",
                    "javascriptreact", "go", "rust", "java", "kotlin",
                    "c", "cpp", "swift", "ruby", "php", "protobuf"):
        return FileType.SOURCE

    conf_names = {".env.example", "docker-compose.yml", "docker-compose.yaml",
                  "Dockerfile", ".gitlab-ci.yml", ".github"}
    if fname in conf_names or language in ("yaml", "json", "xml", "sql", "dockerfile", "terraform"):
        return FileType.CONFIG

    if language == "markdown":
        return FileType.DOCUMENTATION

    return FileType.UNKNOWN
