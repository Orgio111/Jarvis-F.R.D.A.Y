"""
JARVIS Memory Fabric — Multi-layered cognitive memory architecture.

Memory layers:
  - Episodic:  past executions, conversations, workflows (what happened)
  - Semantic:  concepts, embeddings, architecture knowledge (what is true)
  - Procedural: successful workflows, optimized strategies (how to do it)

Integration:
  - Redis:      active context, short-term buffer
  - PostgreSQL: structured system state, user data
  - FAISS/Qdrant: vector intelligence, semantic search
"""

from memory_fabric.fabric import MemoryFabric, MemoryLayer, MemoryEntry, MemoryQuery, FabricConfig

__all__ = [
    "MemoryFabric",
    "MemoryLayer",
    "MemoryEntry",
    "MemoryQuery",
    "FabricConfig",
]
