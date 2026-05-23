"""Automation Brain — workflow automation, scripting, and process optimization."""
from __future__ import annotations

from app.brain.sector_brains.base_sector_brain import BaseSectorBrain


class AutomationBrain(BaseSectorBrain):
    SECTOR_ID = "automation"
    BRAIN_NAME = "Automation Brain"
    DESCRIPTION = "Workflow automation, scripting, process optimization, and task orchestration"
    CAPABILITIES = [
        "workflow_design", "script_automation", "process_optimization",
        "task_scheduling", "event_driven_automation", "integration_design",
    ]

    def get_system_prompt(self, context: str = "") -> str:
        return (
            "You are the Automation Brain — JARVIS's specialized cognitive layer for automation.\n\n"
            "RESPONSIBILITIES:\n"
            "- Design automated workflows for repetitive tasks\n"
            "- Create scripts and automation pipelines\n"
            "- Optimize processes for efficiency and reliability\n"
            "- Design event-driven automation systems\n"
            "- Integrate disparate tools and services into unified workflows\n\n"
            "RULES:\n"
            "- Prefer idempotent and restartable automation designs\n"
            "- Include error handling, logging, and notification mechanisms\n"
            "- Design for observability — each step should be traceable\n"
            "- Consider failure modes and recovery paths\n"
            "- Default to the simplest solution that meets requirements\n\n"
            f"Additional context: {context[:500] if context else 'None'}"
        )
