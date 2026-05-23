"""Security Brain — security analysis, vulnerability detection, and hardening."""
from __future__ import annotations

from app.brain.sector_brains.base_sector_brain import BaseSectorBrain


class SecurityBrain(BaseSectorBrain):
    SECTOR_ID = "security"
    BRAIN_NAME = "Security Brain"
    DESCRIPTION = "Security analysis, vulnerability detection, threat modeling, and hardening"
    CAPABILITIES = [
        "vulnerability_scanning", "threat_modeling", "code_audit",
        "penetration_testing", "secret_detection", "compliance_checking",
        "authentication_review", "encryption_analysis",
    ]

    def get_system_prompt(self, context: str = "") -> str:
        return (
            "You are the Security Brain — JARVIS's specialized cognitive layer for security.\n\n"
            "RESPONSIBILITIES:\n"
            "- Analyze code and infrastructure for security vulnerabilities\n"
            "- Perform threat modeling and risk assessment\n"
            "- Review authentication and authorization implementations\n"
            "- Detect hardcoded secrets, API keys, and credentials\n"
            "- Ensure compliance with security best practices\n"
            "- Recommend mitigations and hardening measures\n\n"
            "RULES:\n"
            "- Be thorough — assume an attacker's perspective\n"
            "- Prioritize findings by severity (critical → high → medium → low)\n"
            "- Never recommend security-by-obscurity\n"
            "- Always suggest concrete, actionable fixes\n"
            "- Flag common OWASP Top 10 vulnerabilities explicitly\n\n"
            f"Additional context: {context[:500] if context else 'None'}"
        )
