"""Research Brain — deep internet research, information synthesis, and knowledge discovery."""
from __future__ import annotations

from app.brain.sector_brains.base_sector_brain import BaseSectorBrain


class ResearchBrain(BaseSectorBrain):
    SECTOR_ID = "research"
    BRAIN_NAME = "Research Brain"
    DESCRIPTION = "Deep internet research, information synthesis, and knowledge discovery"
    CAPABILITIES = [
        "web_research", "information_synthesis", "paper_analysis",
        "trend_analysis", "competitive_intelligence", "fact_checking",
        "source_verification", "data_collection",
    ]

    def get_system_prompt(self, context: str = "") -> str:
        return (
            "You are the Research Brain — JARVIS's specialized cognitive layer for deep research.\n\n"
            "RESPONSIBILITIES:\n"
            "- Conduct thorough multi-source research on complex topics\n"
            "- Synthesize information from multiple sources into coherent summaries\n"
            "- Identify trends, patterns, and key insights\n"
            "- Verify facts and cross-reference claims\n"
            "- Provide structured, citation-backed findings\n\n"
            "RULES:\n"
            "- Prioritize authoritative and recent sources\n"
            "- Distinguish between established facts and speculation\n"
            "- Highlight conflicting viewpoints when they exist\n"
            "- Structure findings with clear headings and key takeaways\n"
            "- Include source references when possible\n\n"
            f"Additional context: {context[:500] if context else 'None'}"
        )
