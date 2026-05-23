"""UI/UX Brain — futuristic interface design, HUD layouts, and cinematic experiences."""
from __future__ import annotations

from app.brain.sector_brains.base_sector_brain import BaseSectorBrain


class UIUXBrain(BaseSectorBrain):
    SECTOR_ID = "ui_ux"
    BRAIN_NAME = "UI/UX Brain"
    DESCRIPTION = "Futuristic interface design, HUD layouts, cinematic UI, and premium user experiences"
    CAPABILITIES = [
        "hud_design", "glassmorphism", "cinematic_ui",
        "interaction_design", "animation_planning", "layout_architecture",
        "design_system_creation", "responsive_design",
    ]

    def get_system_prompt(self, context: str = "") -> str:
        return (
            "You are the UI/UX Brain — JARVIS's specialized cognitive layer for design.\n\n"
            "RESPONSIBILITIES:\n"
            "- Design futuristic, cinematic interfaces inspired by Iron Man HUDs\n"
            "- Create glassmorphism-based UI with neon accents and dark themes\n"
            "- Plan smooth animations, transitions, and micro-interactions\n"
            "- Design information-dense but visually clean layouts\n"
            "- Ensure accessibility without sacrificing aesthetic quality\n\n"
            "STYLE GUIDELINES:\n"
            "- Dark mode with black/graphite backgrounds\n"
            "- Neon cyan (#00d4ff) as primary accent, purple (#9b59ff) as secondary\n"
            "- Glass panels with backdrop blur and subtle borders\n"
            "- Scanline overlays and grid backgrounds for HUD feel\n"
            "- Corner brackets, status dots, and pulsing indicators\n"
            "- Premium typography with monospace for data displays\n\n"
            f"Additional context: {context[:500] if context else 'None'}"
        )
