"""Code Indexing — Semantic repo indexing, AST analysis, and vector code search.

Inspired by Codebuff (file-picker) and Cocoindex-Code (semantic code understanding).
"""

from app.code_indexing.indexer import IndexableFile, FileType, walk_repo, project_root, read_file_safe
from app.code_indexing.chunker import CodeChunk, chunk_file
from app.code_indexing.embedder import embed_chunks, embed_query, embed_dimension
from app.code_indexing.vector_store import init_index, add_chunks, search, search_by_symbol, search_by_file, status, clear
from app.code_indexing.search import unified_search, file_search
from app.code_indexing.analyzer import analyze_architecture, analyze_file, search_architecture
from app.code_indexing.dependency_graph import build_dependency_graph, get_dependencies

__all__ = [
    "IndexableFile", "FileType", "walk_repo", "project_root", "read_file_safe",
    "CodeChunk", "chunk_file",
    "embed_chunks", "embed_query", "embed_dimension",
    "init_index", "add_chunks", "search", "search_by_symbol", "search_by_file", "status", "clear",
    "unified_search", "file_search",
    "analyze_architecture", "analyze_file", "search_architecture",
    "build_dependency_graph", "get_dependencies",
]
