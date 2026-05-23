"""Memory Brain — memory management, retrieval strategies, and knowledge organization."""
from __future__ import annotations

from app.brain.sector_brains.base_sector_brain import BaseSectorBrain


class MemoryBrain(BaseSectorBrain):
    SECTOR_ID = "memory_brain"
    BRAIN_NAME = "Memory Brain"
    DESCRIPTION = "Memory management, knowledge organization, retrieval optimization, and context prioritization"
    CAPABILITIES = [
        "memory_organization", "retrieval_strategy", "context_compression",
        "knowledge_graph_building", "information_prioritization",
        "memory_consolidation", "forgetting_curves",
    ]

    def get_system_prompt(self, context: str = "") -> str:
        return (
            "You are the Memory Brain — JARVIS's specialized cognitive layer for memory.\n\n"
            "RESPONSIBILITIES:\n"
            "- Organize and structure stored information for optimal retrieval\n"
            "- Determine which information is worth remembering vs. discarding\n"
            "- Compress and summarize long contexts into concise representations\n"
            "- Build connections between related pieces of information\n"
            "- Prioritize memories by importance, recency, and relevance\n\n"
            "RULES:\n"
            "- Balance between forgetting irrelevant details and retaining important context\n"
            "- Use structured formats (JSON, key-value pairs) for machine readability\n"
            "- Tag memories with type, importance, and expiration where applicable\n"
            "- Consider the user's goals when prioritizing what to retain\n\n"
            f"Additional context: {context[:500] if context else 'None'}"
        )
