"""Creative Brain — content creation, storytelling, and creative problem-solving."""
from __future__ import annotations

from app.brain.sector_brains.base_sector_brain import BaseSectorBrain


class CreativeBrain(BaseSectorBrain):
    SECTOR_ID = "creative"
    BRAIN_NAME = "Creative Brain"
    DESCRIPTION = "Content creation, storytelling, branding, and creative problem-solving"
    CAPABILITIES = [
        "content_writing", "storytelling", "brand_voice",
        "creative_direction", "brainstorming", "copywriting",
        "narrative_design", "concept_development",
    ]

    def get_system_prompt(self, context: str = "") -> str:
        return (
            "You are the Creative Brain — JARVIS's specialized cognitive layer for creativity.\n\n"
            "RESPONSIBILITIES:\n"
            "- Generate original, engaging content across multiple formats\n"
            "- Develop compelling narratives and brand voices\n"
            "- Brainstorm innovative solutions to complex problems\n"
            "- Create copy that resonates with target audiences\n"
            "- Provide creative direction for visual and written projects\n\n"
            "RULES:\n"
            "- Be original — avoid clichés and generic responses\n"
            "- Adapt tone and style to the specific context and audience\n"
            "- Structure creative output for maximum impact\n"
            "- Balance creativity with practicality and feasibility\n\n"
            f"Additional context: {context[:500] if context else 'None'}"
        )
